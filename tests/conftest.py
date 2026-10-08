from pathlib import Path
from types import SimpleNamespace
import os,json,pytest,allure
from framework.client import ROOT,Db,Api,Actor,product,stock,evidence,redact

@pytest.fixture(scope='session')
def db():
    db=Db()
    assert db.query('SELECT DATABASE() AS db')[0]['db']=='litemall_qa'
    yield db
    db.close()

@pytest.fixture
def guest():
    api=Api(); yield api; api.close()

@pytest.fixture
def sut(db):
    p=product(db); before=stock(db,p['id']); actors=[]
    def new_actor():
        actor=Actor.create(db); actors.append(actor); return actor
    ctx=SimpleNamespace(db=db,product=p,baseline=before,new_actor=new_actor)
    ctx.user=new_actor()
    yield ctx
    errors=[]
    for actor in reversed(actors):
        try: actor.cleanup()
        except Exception as error: errors.append(str(error))
    assert not errors, 'Cleanup failed: '+str(errors)
    assert stock(db,p['id'])==before, 'Stock was not restored during cleanup'

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item,call):
    outcome=yield
    report=outcome.get_result()
    setattr(item,'rep_'+report.when,report)
    if report.when=='call' or (report.when in ['setup','teardown'] and report.failed):
        evidence('pytest-results',{'nodeid':report.nodeid,'phase':report.when,'outcome':report.outcome,
            'duration':report.duration,'failure':redact(str(report.longrepr)) if report.failed else None})
