import json,sqlite3,tempfile,threading,time
from pathlib import Path
from lei_signal.storage.write_tx import TrackedConnection,active_writers_snapshot
with tempfile.TemporaryDirectory() as temp:
 p=str(Path(temp)/"test.db")
 h=sqlite3.connect(p,check_same_thread=False);h.execute("CREATE TABLE t(x)");h.execute("BEGIN IMMEDIATE")
 c=sqlite3.connect(p,factory=TrackedConnection)
 def release():
  time.sleep(.3);h.commit()
 t=threading.Thread(target=release);t.start();start=time.perf_counter()
 c.execute("INSERT INTO t VALUES(1)");elapsed=(time.perf_counter()-start)*1000
 snap=active_writers_snapshot();result={"write_elapsed_ms":elapsed,"registered_held_ms":snap[0]["held_ms"]}
 print(json.dumps(result));c.rollback();c.close();t.join();h.close()
