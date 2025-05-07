const fs = require("fs");
const path = require("path");

// Paths to the files
const nativePath = path.join(__dirname, "../node_modules/rollup/dist/native.js");
const esNativePath = path.join(__dirname, "../node_modules/rollup/dist/es/native.js");
const esParseAstPath = path.join(__dirname, "../node_modules/rollup/dist/es/shared/parseAst.js");
const parseAstPath = path.join(__dirname, "../node_modules/rollup/dist/shared/parseAst.js");

// Ensure directories exist
const nativeDirES = path.dirname(esNativePath);
const parseAstDirES = path.dirname(esParseAstPath);
const parseAstDir = path.dirname(parseAstPath);

try {
  if (!fs.existsSync(nativeDirES)) {
    fs.mkdirSync(nativeDirES, { recursive: true });
    console.log(`✅ Created directory ${nativeDirES}`);
  }
  if (!fs.existsSync(parseAstDirES)) {
    fs.mkdirSync(parseAstDirES, { recursive: true });
    console.log(`✅ Created directory ${parseAstDirES}`);
  }
  if (!fs.existsSync(parseAstDir)) {
    fs.mkdirSync(parseAstDir, { recursive: true });
    console.log(`✅ Created directory ${parseAstDir}`);
  }
} catch (err) {
  console.error(`❌ Failed to create directories: ${err.message}`);
}

// Patch CJS version of native.js
if (fs.existsSync(nativePath)) {
  try {
    const cjsStub = `
module.exports = {
  parse: () => {
    const buffer = new Uint8Array(4);
    buffer.buffer = new ArrayBuffer(4);
    const array = new Uint32Array(buffer.buffer);
    array[0] = 0;
    return buffer;
  },
  parseAsync: async () => {
    const buffer = new Uint8Array(4);
    buffer.buffer = new ArrayBuffer(4);
    const array = new Uint32Array(buffer.buffer);
    array[0] = 0;
    return buffer;
  },
  xxhashBase64Url: () => '',
  xxhashBase36: () => '',
  xxhashBase16: () => ''
};
`;
    fs.writeFileSync(nativePath, cjsStub);
    console.log(`✅ Patched dist/native.js with CJS stub`);
  } catch (err) {
    console.error(`❌ Failed to patch dist/native.js`, err);
  }
} else {
  console.error(`❌ dist/native.js not found!`);
}

// Patch ESM version of native.js
if (fs.existsSync(esNativePath)) {
  try {
    const esmStub = `export default {
  parse: () => {
    const buffer = new Uint8Array(4);
    buffer.buffer = new ArrayBuffer(4);
    const array = new Uint32Array(buffer.buffer);
    array[0] = 0;
    return buffer;
  },
  parseAsync: async () => {
    const buffer = new Uint8Array(4);
    buffer.buffer = new ArrayBuffer(4);
    const array = new Uint32Array(buffer.buffer);
    array[0] = 0;
    return buffer;
  },
  xxhashBase64Url: () => '',
  xxhashBase36: () => '',
  xxhashBase16: () => ''
};

// For compatibility
export const parse = () => {
  const buffer = new Uint8Array(4);
  buffer.buffer = new ArrayBuffer(4);
  const array = new Uint32Array(buffer.buffer);
  array[0] = 0;
  return buffer;
};

export const parseAsync = async () => {
  const buffer = new Uint8Array(4);
  buffer.buffer = new ArrayBuffer(4);
  const array = new Uint32Array(buffer.buffer);
  array[0] = 0;
  return buffer;
};

export const xxhashBase64Url = () => '';
export const xxhashBase36 = () => '';
export const xxhashBase16 = () => '';
`;
    fs.writeFileSync(esNativePath, esmStub);
    console.log(`✅ Patched es/native.js with ESM stub`);
  } catch (err) {
    console.error(`❌ Failed to patch es/native.js`, err);
  }
} else if (!fs.existsSync(path.dirname(esNativePath))) {
  try {
    // Create the directory if it doesn't exist
    fs.mkdirSync(path.dirname(esNativePath), { recursive: true });
    
    const esmStub = `export default {
  parse: () => {
    const buffer = new Uint8Array(4);
    buffer.buffer = new ArrayBuffer(4);
    const array = new Uint32Array(buffer.buffer);
    array[0] = 0;
    return buffer;
  },
  parseAsync: async () => {
    const buffer = new Uint8Array(4);
    buffer.buffer = new ArrayBuffer(4);
    const array = new Uint32Array(buffer.buffer);
    array[0] = 0;
    return buffer;
  },
  xxhashBase64Url: () => '',
  xxhashBase36: () => '',
  xxhashBase16: () => ''
};

// For compatibility
export const parse = () => {
  const buffer = new Uint8Array(4);
  buffer.buffer = new ArrayBuffer(4);
  const array = new Uint32Array(buffer.buffer);
  array[0] = 0;
  return buffer;
};

export const parseAsync = async () => {
  const buffer = new Uint8Array(4);
  buffer.buffer = new ArrayBuffer(4);
  const array = new Uint32Array(buffer.buffer);
  array[0] = 0;
  return buffer;
};

export const xxhashBase64Url = () => '';
export const xxhashBase36 = () => '';
export const xxhashBase16 = () => '';
`;
    fs.writeFileSync(esNativePath, esmStub);
    console.log(`✅ Created and patched es/native.js with ESM stub`);
  } catch (err) {
    console.error(`❌ Failed to create and patch es/native.js`, err);
  }
}

// Patch the parseAst.js file to fix ESM import
if (fs.existsSync(esParseAstPath)) {
  try {
    let content = fs.readFileSync(esParseAstPath, 'utf8');
    
    // Fix ESM import issue by replacing the import statement
    content = content.replace(
      /import \{ parse, parseAsync \} from '\.\.\/\.\.\/native\.js';/,
      `import pkg from '../../native.js';
const { parse, parseAsync } = pkg;`
    );
    
    fs.writeFileSync(esParseAstPath, content);
    console.log(`✅ Fixed ESM import in es/shared/parseAst.js`);
  } catch (err) {
    console.error(`❌ Failed to fix ESM import in es/shared/parseAst.js`, err);
  }
}

console.log("✅ Rollup native module patches completed");