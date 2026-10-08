from pathlib import Path
import json,sys,xml.etree.ElementTree as ET
root=Path(sys.argv[1])
xml=ET.parse(root/'junit.xml').getroot()
cases=list(xml.iter('testcase'))
result={'total':len(cases),'passed':0,'failed':0,'skipped':0,'errors':0,'tests':[]}
for case in cases:
    status='passed'
    for tag in ['failure','error','skipped']:
        if case.find(tag) is not None:
            status={'failure':'failed','error':'errors','skipped':'skipped'}[tag]; break
    result[status]+=1
    result['tests'].append({'name':case.attrib['name'],'classname':case.attrib['classname'],'status':status,'seconds':float(case.attrib.get('time',0))})
(root/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='tests'},ensure_ascii=False))
