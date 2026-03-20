"use strict";
const fs = require("fs");
const path = require("path");
const CryptoJS = require("crypto-js");
const { webcrypto } = require("crypto");

const WASM_PATH = path.join(__dirname, "module.wasm");

function readString(memory, ptr) {
  if (!ptr) return null;
  const u32 = new Uint32Array(memory.buffer);
  const u16 = new Uint16Array(memory.buffer);
  
  let endOffStr = ptr + u32[(ptr - 4) >>> 2]; 
  let t = endOffStr >>> 1; 
  let n = ptr >>> 1;       
  let s = "";
  
  if (t - n > 5000000 || t - n < 0) return null;

  for (; t - n > 1024;) {
    s += String.fromCharCode(...u16.subarray(n, n += 1024));
  }
  return s + String.fromCharCode(...u16.subarray(n, t));
}

function writeString(exports, memory, str) {
  const ptr = exports.__new(str.length << 1, 2) >>> 0;
  const u16 = new Uint16Array(memory.buffer);
  for (let i = 0; i < str.length; i++) {
    u16[(ptr >>> 1) + i] = str.charCodeAt(i);
  }
  return ptr;
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
  }
  return bytes;
}

function bytesToHex(bytes) {
  return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

async function decrypt(ciphertextHex, tmdbId) {
  const wasmBytes = fs.readFileSync(WASM_PATH);
  
  const env = {
    seed: () => Date.now() * Math.random(),
    abort() {}
  };

  const { instance } = await WebAssembly.instantiate(wasmBytes, { env });
  const exp = instance.exports;
  const memory = exp.memory;

  const servePtr = exp.serve() >>> 0;
  let serveCode = readString(memory, servePtr);

  serveCode = serveCode.replace(/_0x24\(\),_0x36\(/g, '_0x36(');

  const fakeWindow = { location: { hostname: "cineby.gd", href: "https://cineby.gd/" } };
  const fn = new Function("window", "crypto", "TextEncoder", serveCode);
  fn(fakeWindow, webcrypto, TextEncoder);
  
  await new Promise(r => setTimeout(r, 100));
  const hash = String(fakeWindow.hash);
  if (!hash || hash === "undefined") {
      throw new Error("Failed to get hash");
  }

  const hashPtr = writeString(exp, memory, hash);
  if (!exp.verify(hashPtr)) {
    throw new Error("WASM verify failed");
  }

  const ctPtr = writeString(exp, memory, ciphertextHex);
  const resPtr = exp.decrypt(ctPtr, parseInt(tmdbId, 10)) >>> 0;
  let wasmDecryptedStr = readString(memory, resPtr);
  if (!wasmDecryptedStr) {
      throw new Error("WASM decrypt returned null");
  }

  const pt = CryptoJS.AES.decrypt(wasmDecryptedStr, '').toString(CryptoJS.enc.Utf8);
  if (!pt) throw new Error("CryptoJS decryption yielded empty string");
  
  return JSON.parse(pt);
}

async function main() {
  const argHex = process.argv[2];
  const tmdbId = process.argv[3];
  try {
      const result = await decrypt(argHex, tmdbId);
      console.log(JSON.stringify({success: true, data: result}));
  } catch(e) {
      console.log(JSON.stringify({success: false, error: e.message}));
  }
}

if (require.main === module) {
  main();
}

module.exports = { decrypt };
