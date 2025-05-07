/**
 * Empty Module Mock for native dependencies
 * This file is used in the Docker build process to create empty versions of 
 * native modules that cause problems when building in a Docker container.
 */

module.exports = () => {
  return require("module").Module._extensions[".js"];
};

module.exports.lmdb = {
  open: () => ({}),
  OPCODES: {},
  getAddress: () => {}
};

module.exports.default = module.exports;