from pathlib import Path
import json,shutil
root=Path(__file__).resolve().parents[1]
src=root/'vendor/litemall-master/litemall-vue'
package=src/'package.json'
data=json.loads(package.read_text(encoding='utf-8'))
data['dependencies']['regenerator-runtime']='^0.14.1'
package.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copyfile(root/'config/frontend-package-lock.json',src/'package-lock.json')
print('Applied recorded deployment-only dependency fix and frozen frontend lock')
