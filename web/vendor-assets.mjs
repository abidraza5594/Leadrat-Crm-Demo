import {copyFile, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
for (const file of ['dist/js/intlTelInput.min.js','dist/js/utils.js','dist/css/intlTelInput.css','dist/img/flags.webp','dist/img/flags@2x.webp','LICENSE']) {
  const target=path.join(root,'vendor/intl-tel-input',file.replace(/^dist\//,''));
  await mkdir(path.dirname(target),{recursive:true});
  await copyFile(path.join(root,'node_modules/intl-tel-input',file),target);
}
console.log('Copied pinned intl-tel-input browser assets.');
