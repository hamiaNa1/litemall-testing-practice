from pathlib import Path
import os,re,json,zipfile
import pytest,allure
from playwright.sync_api import sync_playwright
from framework.client import ROOT,config,redact,evidence

@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as pw:
        exe=os.environ.get('CHROMIUM_EXECUTABLE')
        if not exe:
            cached=list(Path('D:/Codex/Cache/ms-playwright').glob('chromium-*/chrome-win64/chrome.exe'))
            if cached: exe=str(cached[-1])
        options={'headless':True}
        if exe: options['executable_path']=exe
        browser=pw.chromium.launch(**options)
        yield browser
        browser.close()

def sanitize_trace(source,target,secrets):
    with zipfile.ZipFile(source) as original,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as safe:
        for entry in original.infolist():
            content=original.read(entry.filename)
            try:
                text=content.decode('utf-8')
                for secret in secrets:
                    if secret: text=text.replace(secret,'[REDACTED]')
                if entry.filename.endswith(('.trace','.network')):
                    text='\n'.join(json.dumps(redact(json.loads(line)),ensure_ascii=False) for line in text.splitlines() if line)
                else:
                    try: text=json.dumps(redact(json.loads(text)),ensure_ascii=False)
                    except ValueError: pass
                content=text.encode('utf-8')
            except (UnicodeDecodeError,ValueError): pass
            safe.writestr(entry,content)

@pytest.fixture
def ui_page(browser,request):
    folder=Path(os.environ['EVIDENCE_DIR'])/'ui'/re.sub(r'[^a-zA-Z0-9_-]','_',request.node.name)
    folder.mkdir(parents=True,exist_ok=True)
    ctx=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    ctx.tracing.start(screenshots=True,snapshots=True,sources=True)
    page=ctx.new_page(); page.set_default_timeout(15000)
    errors=[]; secrets=[v for k,v in config().items() if 'PASSWORD' in k]
    page.on('pageerror',lambda error:errors.append(str(error)))
    def capture_token(response):
        if '/wx/auth/login' in response.url:
            try:
                token=response.json().get('data',{}).get('token')
                if token: secrets.append(token)
            except Exception: pass
    page.on('response',capture_token)
    yield page
    failed=getattr(request.node,'rep_call',None) and request.node.rep_call.failed
    png=folder/('failure.png' if failed else 'success.png')
    page.screenshot(path=str(png),full_page=True)
    allure.attach.file(str(png),name='Failure screenshot' if failed else 'Final page',attachment_type=allure.attachment_type.PNG)
    raw=ROOT/'.runtime'/('trace-'+request.node.name+'.zip')
    ctx.tracing.stop(path=str(raw)); ctx.close()
    target=folder/'trace.zip'
    sanitize_trace(raw,target,secrets); raw.unlink()
    allure.attach.file(str(target),name='Redacted Playwright Trace',attachment_type='application/zip',extension='zip')
    evidence('ui-browser',{'test':request.node.nodeid,'page_errors':redact(errors),'screenshot':str(png),'trace':str(target)})
