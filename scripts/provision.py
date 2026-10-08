"""Provision only this project's private MySQL instance. Never touches port 3306."""
from pathlib import Path
import os, re, secrets, subprocess, time, json, socket
from dotenv import dotenv_values
import pymysql

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(os.environ.get('MYSQL_BIN', 'D:/DevTools/MySQL/mysql-8.4.11-winx64/bin'))
DATA = ROOT / '.runtime/mysql-data'
ENV = ROOT / '.env'
ROOT.joinpath('.runtime').mkdir(exist_ok=True)
ROOT.joinpath('evidence/environment').mkdir(parents=True, exist_ok=True)
if not ENV.exists():
    ENV.write_text('\n'.join([
        'BASE_URL=http://127.0.0.1:8080', 'UI_URL=http://127.0.0.1:6255',
        'DB_HOST=127.0.0.1', 'DB_PORT=13306', 'DB_NAME=litemall_qa',
        'DB_USER=qa_local', 'DB_PASSWORD='+secrets.token_hex(24),
        'DB_ROOT_PASSWORD='+secrets.token_hex(24),
        'TEST_USERNAME=qa_primary', 'TEST_PASSWORD='+secrets.token_hex(16),
        'OTHER_USERNAME=qa_secondary', 'OTHER_PASSWORD='+secrets.token_hex(16),
    ])+'\n', encoding='utf-8')
c = dotenv_values(ENV)
port = int(c['DB_PORT'])
assert port == 13306 and c['DB_NAME'] == 'litemall_qa'
fresh = not DATA.exists()
if fresh:
    result = subprocess.run([str(BIN/'mysqld.exe'), '--no-defaults', '--initialize-insecure',
        '--basedir='+str(BIN.parent), '--datadir='+str(DATA)], capture_output=True, text=True)
    (ROOT/'evidence/environment/mysql-initialize.log').write_text(result.stdout+result.stderr, encoding='utf-8')
    result.check_returncode()
with socket.socket() as sock:
    running = sock.connect_ex(('127.0.0.1', port)) == 0
if not running:
    log = open(ROOT/'evidence/environment/mysql-process.log', 'ab')
    p = subprocess.Popen([str(BIN/'mysqld.exe'), '--no-defaults', '--basedir='+str(BIN.parent),
        '--datadir='+str(DATA), '--port='+str(port), '--bind-address=127.0.0.1',
        '--mysqlx=OFF', '--character-set-server=utf8mb4', '--default-time-zone=+08:00',
        '--log-error='+str(ROOT/'evidence/environment/mysql-server.log')], stdout=log, stderr=log,
        creationflags=subprocess.CREATE_NO_WINDOW)
    (ROOT/'.runtime/mysql.pid').write_text(str(p.pid))
for attempt in range(60):
    try:
        db = pymysql.connect(host='127.0.0.1', port=port, user='root',
            password='' if fresh else c['DB_ROOT_PASSWORD'], autocommit=True)
        break
    except pymysql.err.OperationalError:
        time.sleep(1)
else:
    raise RuntimeError('Private MySQL failed to start; inspect mysql-server.log')
with db.cursor() as cur:
    cur.execute('SELECT @@datadir')
    actual_data = Path(cur.fetchone()[0]).resolve()
    assert actual_data == DATA.resolve(), 'Refusing to provision a different MySQL instance'
    if fresh:
        cur.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (c['DB_ROOT_PASSWORD'],))
    cur.execute('CREATE DATABASE IF NOT EXISTS litemall_qa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='litemall_qa'")
    empty = cur.fetchone()[0] == 0
    cur.execute("CREATE USER IF NOT EXISTS 'qa_local'@'localhost' IDENTIFIED BY %s", (c['DB_PASSWORD'],))
    cur.execute("GRANT ALL PRIVILEGES ON litemall_qa.* TO 'qa_local'@'localhost'")
db.close()
if empty:
    src = ROOT/'vendor/litemall-master/litemall-db/sql'
    sql = '\n'.join((src/name).read_text(encoding='utf-8') for name in ['litemall_table.sql','litemall_data.sql'])
    # Imports apply only to a verified empty project database. Upstream DROP statements are removed.
    sql = re.sub(r'^DROP TABLE IF EXISTS .*?;\s*$', '', sql, flags=re.M)
    assert not re.search(r'\b(DROP DATABASE|DROP TABLE|TRUNCATE|USE\s+litemall\b)', sql, re.I)
    env = dict(os.environ, MYSQL_PWD=c['DB_PASSWORD'])
    p = subprocess.run([str(BIN/'mysql.exe'), '--no-defaults', '-h127.0.0.1', '-P'+str(port),
        '-uqa_local', '--default-character-set=utf8mb4', 'litemall_qa'], input=sql.encode(),
        capture_output=True, env=env)
    (ROOT/'evidence/environment/mysql-import.log').write_bytes(p.stdout+p.stderr)
    p.check_returncode()
db = pymysql.connect(host='127.0.0.1', port=port, user=c['DB_USER'], password=c['DB_PASSWORD'],
    database=c['DB_NAME'], autocommit=True, charset='utf8mb4')
import bcrypt
with db.cursor() as cur:
    for prefix in ['TEST','OTHER']:
        cur.execute('SELECT id FROM litemall_user WHERE username=%s', (c[prefix+'_USERNAME'],))
        if not cur.fetchone():
            cur.execute('INSERT INTO litemall_user (username,password,nickname,gender,user_level,status,add_time,update_time,deleted) VALUES (%s,%s,%s,0,0,0,NOW(),NOW(),0)',
                (c[prefix+'_USERNAME'], bcrypt.hashpw(c[prefix+'_PASSWORD'].encode(), bcrypt.gensalt(prefix=b'2a')).decode(), c[prefix+'_USERNAME']))
    cur.execute('SELECT COUNT(*) FROM litemall_goods WHERE deleted=0 AND is_on_sale=1')
    goods = cur.fetchone()[0]
db.close()
# Credentials remain solely in ignored .env. Spring loads them through environment variables.
(ROOT/'config').mkdir(exist_ok=True)
(ROOT/'config/application-qa.yml').write_text('''server:
  address: 127.0.0.1
  port: 8080
spring:
  datasource:
    druid:
      url: jdbc:mysql://127.0.0.1:13306/litemall_qa?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true&useSSL=false
      username: ${DB_USER}
      password: ${DB_PASSWORD}
litemall:
  wx:
    app-id: local-test-placeholder
    app-secret: local-test-placeholder
  storage:
    active: local
  notify:
    mail:
      enable: false
    sms:
      enable: false
''', encoding='utf-8')
print(json.dumps({'private_mysql_port':port, 'database':c['DB_NAME'], 'sale_goods':goods, 'seeded_test_accounts':2}))
