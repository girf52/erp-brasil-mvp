const { execSync } = require('child_process');
const path = require('path');
const frontendDir = path.dirname(require.resolve('./package.json'));
process.chdir(frontendDir);
const args = process.argv.slice(2).join(' ');
const viteBin = path.join(frontendDir, 'node_modules', '.bin', 'vite');
require('child_process').execFileSync(process.execPath, [
  path.join(frontendDir, 'node_modules', 'vite', 'bin', 'vite.js'),
  ...process.argv.slice(2)
], { stdio: 'inherit', cwd: frontendDir });
