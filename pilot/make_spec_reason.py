"""Writes spec_reason.json: reasoning-focused cases (arithmetic, logic, version ranges,
modality/quantifier shifts, exceptions, transitivity, temporal). Kept as code because the
claim list is long; build.py validates every quote/anchor against the sources."""
import json, pathlib
S, C, U = "SUPPORTED", "CONTRADICTED", "UNSUPPORTED"
def cl(text, anchor, verdict, typ, ev=(), mode="any", note=None, contestable=False):
    d = {"text": text, "anchor": anchor, "verdict": verdict, "type": typ, "evidence": [{"p": p, "quote": q} for p, q in ev]}
    if mode != "any": d["evidence_mode"] = mode
    if note: d["note"] = note
    if contestable: d["contestable"] = True
    return d
cases = []

# ---------------- R1: PostgreSQL XID wraparound arithmetic ----------------
P = ["pg:21", "pg:22", "pg:29", "pg:30", "pg:31", "pg:32", "pg:37", "pg:38", "pg:39"]
A = ("Because transaction IDs are only 32 bits wide, the XID space holds about 4 billion values, and every normal XID has roughly two billion older and two billion newer XIDs. "
     "That is why every table must be vacuumed at least once every two billion transactions; running past that without vacuuming means permanent, unrecoverable data loss. "
     "With the default autovacuum_freeze_max_age of 200 million transactions, the anti-wraparound autovacuum kicks in after only about 10% of that two-billion window. "
     "The effective maximum for vacuum_freeze_table_age is 95% of autovacuum_freeze_max_age, so with the default it can be at most 180 million. "
     "If autovacuum still fails, warnings start when the oldest XIDs are forty million transactions from wraparound and new XIDs are refused once fewer than three million remain, leaving a 37-million-transaction window between the first warning and the hard stop. "
     "Once XID assignment stops, no new transactions of any kind can be started.")
cases.append({"id": "reason-01-pg-xid-arithmetic", "categories": ["reasoning"], "passages": P, "answer": A, "claims": [
  cl("PostgreSQL transaction IDs are 32 bits wide.", "transaction IDs are only 32 bits wide", S, "paraphrase", [(0, "since transaction IDs have limited size (32 bits)")]),
  cl("The 32-bit XID space holds about 4 billion values.", "the XID space holds about 4 billion values", S, "arithmetic",
     [(0, "since transaction IDs have limited size (32 bits)"), (0, "a cluster that runs for a long time (more than 4 billion transactions) would suffer transaction ID wraparound")], note="2^32 is about 4.3 billion."),
  cl("Every normal XID has about two billion older and two billion newer XIDs.", "every normal XID has roughly two billion older and two billion newer XIDs", S, "paraphrase",
     [(1, "for every normal XID, there are two billion XIDs that are “older” and two billion that are “newer”")]),
  cl("Every table must be vacuumed at least once every two billion transactions.", "every table must be vacuumed at least once every two billion transactions", S, "paraphrase",
     [(0, "it is necessary to vacuum every table in every database at least once every two billion transactions.")]),
  cl("Running past the wraparound limit without vacuuming causes permanent, unrecoverable data loss.", "running past that without vacuuming means permanent, unrecoverable data loss", C, "exception_ignored",
     [(0, "(Actually the data is still there, but that's cold comfort if you cannot get at it.)")], note="The docs say the data is still there, just invisible.", contestable=True),
  cl("With the default autovacuum_freeze_max_age of 200 million, the anti-wraparound autovacuum kicks in after about 10% of the two-billion window.", "the anti-wraparound autovacuum kicks in after only about 10% of that two-billion window", S, "arithmetic_multi_hop",
     [(5, "(The default, 200 million transactions, translates to about 50MB of pg_xact storage and about 2GB of pg_commit_ts storage.)"), (0, "at least once every two billion transactions.")], mode="all", note="200M / 2B = 10%."),
  cl("With the default autovacuum_freeze_max_age, vacuum_freeze_table_age can be at most 180 million.", "so with the default it can be at most 180 million", C, "arithmetic_error",
     [(4, "The effective maximum for vacuum_freeze_table_age is 0.95 * autovacuum_freeze_max_age"), (5, "(The default, 200 million transactions, translates to about 50MB of pg_xact storage and about 2GB of pg_commit_ts storage.)")], mode="all", note="0.95 * 200M = 190M."),
  cl("There are 37 million transactions between the first wraparound warning and the point where new XIDs are refused.", "leaving a 37-million-transaction window between the first warning and the hard stop", S, "arithmetic_multi_hop",
     [(6, "when the database's oldest XIDs reach forty million transactions from the wraparound point"), (7, "the system will refuse to assign new XIDs once there are fewer than three million transactions left until wraparound")], mode="all", note="40M - 3M = 37M."),
  cl("Once XID assignment stops, no new transactions of any kind can be started.", "Once XID assignment stops, no new transactions of any kind can be started.", C, "exception_ignored",
     [(8, "In this condition any transactions already in progress can continue, but only read-only transactions can be started.")]),
]})

# ---------------- R2: PostgreSQL autovacuum logic ----------------
P = ["pg:29", "pg:54", "pg:55", "pg:56", "pg:57", "pg:61", "pg:64", "pg:17", "pg:18"]
A = ("Autovacuum relies on the statistics collection facility, so if track_counts is off, autovacuum cannot be used; turning track_counts on is by itself enough for autovacuum to work. "
     "Even when autovacuum is disabled, PostgreSQL still invokes it on tables that might contain unfrozen rows with XIDs older than autovacuum_freeze_max_age. "
     "The launcher tries to start one worker per database every autovacuum_naptime seconds, so with 4 databases and autovacuum_naptime set to 60 seconds, a new worker starts about every 15 seconds. "
     "Each database gets at most one worker at a time, and running workers count against max_connections. "
     "Autovacuum processes partitions like ordinary tables, but it does not run ANALYZE on partitioned tables, and it does not issue ANALYZE for foreign tables either. "
     "Normally a conflicting lock request interrupts autovacuum, and the same is true for an autovacuum that is running to prevent transaction ID wraparound.")
cases.append({"id": "reason-02-pg-autovacuum-logic", "categories": ["reasoning"], "passages": P, "answer": A, "claims": [
  cl("If track_counts is off, autovacuum cannot be used.", "if track_counts is off, autovacuum cannot be used", S, "contrapositive", [(1, "autovacuum cannot be used unless track_counts is set to true.")]),
  cl("Turning track_counts on is by itself enough for autovacuum to work.", "turning track_counts on is by itself enough for autovacuum to work", U, "converse_of_only_if", [], note="track_counts is necessary, not stated to be sufficient."),
  cl("Even when autovacuum is disabled, PostgreSQL still invokes it on tables that might contain unfrozen rows with XIDs older than autovacuum_freeze_max_age.", "Even when autovacuum is disabled, PostgreSQL still invokes it on tables that might contain unfrozen rows with XIDs older than autovacuum_freeze_max_age", S, "paraphrase",
     [(0, "(This will happen even if autovacuum is disabled.)")]),
  cl("With 4 databases and autovacuum_naptime set to 60 seconds, a new autovacuum worker starts about every 15 seconds.", "with 4 databases and autovacuum_naptime set to 60 seconds, a new worker starts about every 15 seconds", S, "arithmetic",
     [(2, "(Therefore, if the installation has N databases, a new worker will be launched every autovacuum_naptime/N seconds.)")], note="60 / 4 = 15."),
  cl("Each database gets at most one autovacuum worker at a time.", "Each database gets at most one worker at a time", C, "quantifier_change", [(3, "There is no limit on how many workers might be in a single database")]),
  cl("Running autovacuum workers count against max_connections.", "running workers count against max_connections", C, "negation_flip",
     [(3, "Note that the number of running workers does not count towards max_connections or superuser_reserved_connections limits.")]),
  cl("Autovacuum processes table partitions like ordinary tables.", "Autovacuum processes partitions like ordinary tables", S, "paraphrase", [(5, "(Autovacuum does process table partitions just like other tables.)")]),
  cl("Autovacuum does not run ANALYZE on partitioned tables.", "it does not run ANALYZE on partitioned tables", S, "near_verbatim",
     [(5, "this means that autovacuum does not run ANALYZE on partitioned tables"), (8, "The autovacuum daemon does not issue ANALYZE commands for partitioned tables.")]),
  cl("Autovacuum does not issue ANALYZE for foreign tables.", "it does not issue ANALYZE for foreign tables either", S, "near_verbatim", [(7, "The autovacuum daemon does not issue ANALYZE commands for foreign tables")]),
  cl("An autovacuum running to prevent transaction ID wraparound is interrupted by a conflicting lock request, just like a normal autovacuum.", "the same is true for an autovacuum that is running to prevent transaction ID wraparound", C, "exception_ignored",
     [(6, "the autovacuum is not automatically interrupted.")]),
]})

# ---------------- R3: VACUUM vs VACUUM FULL ----------------
P = ["pg:1", "pg:3", "pg:4", "pg:5", "pg:6", "pg:7", "pg:8", "pg:9"]
A = ("Standard VACUUM can run alongside normal SELECT, INSERT, UPDATE and DELETE traffic, while VACUUM FULL needs an ACCESS EXCLUSIVE lock on the table; VACUUM FULL is also the faster of the two because it compacts the table in a single pass. "
     "Standard VACUUM never returns space to the operating system. "
     "VACUUM FULL, CLUSTER and the table-rewriting forms of ALTER TABLE all temporarily need extra disk space roughly equal to the size of the table, so rewriting a 50 GB table needs about another 50 GB free. "
     "Since the autovacuum daemon never issues VACUUM FULL, a VACUUM FULL that shows up in your logs was not started by autovacuum. "
     "For a table whose entire contents are deleted periodically, TRUNCATE avoids the need for a follow-up VACUUM, at the cost of violating strict MVCC semantics. "
     "Installations with extremely high update rates may vacuum their busiest tables as often as every few minutes, and anyone not using autovacuum is required to run a database-wide VACUUM once a day.")
cases.append({"id": "reason-03-pg-vacuum-full", "categories": ["reasoning"], "passages": P, "answer": A, "claims": [
  cl("Standard VACUUM can run alongside normal SELECT, INSERT, UPDATE and DELETE operations.", "Standard VACUUM can run alongside normal SELECT, INSERT, UPDATE and DELETE traffic", S, "paraphrase",
     [(0, "the standard form of VACUUM can run in parallel with production database operations.")]),
  cl("VACUUM FULL requires an ACCESS EXCLUSIVE lock on the table.", "VACUUM FULL needs an ACCESS EXCLUSIVE lock on the table", S, "near_verbatim", [(0, "VACUUM FULL requires an ACCESS EXCLUSIVE lock on the table it is working on")]),
  cl("VACUUM FULL is faster than standard VACUUM.", "VACUUM FULL is also the faster of the two", C, "reversed_comparison", [(0, "VACUUM FULL can reclaim more disk space but runs much more slowly.")]),
  cl("Standard VACUUM never returns space to the operating system.", "Standard VACUUM never returns space to the operating system.", C, "exception_ignored",
     [(2, "However, it will not return the space to the operating system, except in the special case where one or more pages at the end of a table become entirely free and an exclusive table lock can be easily obtained.")]),
  cl("VACUUM FULL, CLUSTER and table-rewriting ALTER TABLE temporarily need extra disk space roughly equal to the size of the table.", "VACUUM FULL, CLUSTER and the table-rewriting forms of ALTER TABLE all temporarily need extra disk space roughly equal to the size of the table", S, "paraphrase",
     [(6, "Note that they also temporarily use extra disk space approximately equal to the size of the table")]),
  cl("Rewriting a 50 GB table this way needs about another 50 GB of free disk space.", "rewriting a 50 GB table needs about another 50 GB free", S, "instantiation",
     [(6, "Note that they also temporarily use extra disk space approximately equal to the size of the table")]),
  cl("A VACUUM FULL that shows up in the logs was not started by autovacuum.", "a VACUUM FULL that shows up in your logs was not started by autovacuum", S, "contrapositive", [(3, "and in fact will never issue VACUUM FULL.")]),
  cl("For a table whose entire contents are deleted periodically, TRUNCATE avoids the need for a follow-up VACUUM.", "TRUNCATE avoids the need for a follow-up VACUUM", S, "paraphrase",
     [(7, "TRUNCATE removes the entire content of the table immediately, without requiring a subsequent VACUUM or VACUUM FULL to reclaim the now-unused disk space.")]),
  cl("TRUNCATE violates strict MVCC semantics.", "at the cost of violating strict MVCC semantics", S, "paraphrase", [(7, "The disadvantage is that strict MVCC semantics are violated.")]),
  cl("Installations with extremely high update rates may vacuum their busiest tables as often as every few minutes.", "Installations with extremely high update rates may vacuum their busiest tables as often as every few minutes", S, "modality_weakening",
     [(5, "(Some installations with extremely high update rates vacuum their busiest tables as often as once every few minutes.)")]),
  cl("Anyone not using autovacuum is required to run a database-wide VACUUM once a day.", "anyone not using autovacuum is required to run a database-wide VACUUM once a day", U, "modality_strengthening", [],
     note="Docs call it 'a typical approach', not a requirement."),
]})

# ---------------- R4: freezing versions and storage arithmetic ----------------
P = ["pg:23", "pg:24", "pg:32", "pg:25", "pg:33", "pg:45", "pg:48", "pg:53"]
A = ("Before PostgreSQL 9.4, freezing replaced a row's insertion XID with FrozenTransactionId, so on a cluster still running 9.3 frozen rows show up with an xmin of 2. "
     "Newer versions only set a flag bit, mainly to reduce WAL volume, and keep the original xmin, so a cluster that was pg_upgrade'd from 9.3 can never contain rows with xmin 2. "
     "System catalogs can also contain rows with xmin 1, BootstrapTransactionId, which is treated as older than every normal XID. "
     "pg_xact stores two bits of commit status per transaction, so the default horizon of 200 million transactions costs about 50MB, and raising autovacuum_freeze_max_age to its two-billion maximum would grow pg_xact to roughly 2GB. "
     "Multixact member storage can grow to about 20GB before wraparound, and aggressive vacuums start running more often once it passes about half of that. "
     "XID exhaustion and MXID exhaustion both block all write transactions.")
cases.append({"id": "reason-04-pg-freezing-storage", "categories": ["reasoning"], "passages": P, "answer": A, "claims": [
  cl("Before PostgreSQL 9.4, freezing replaced a row's insertion XID with FrozenTransactionId.", "Before PostgreSQL 9.4, freezing replaced a row's insertion XID with FrozenTransactionId", S, "paraphrase",
     [(0, "In PostgreSQL versions before 9.4, freezing was implemented by actually replacing a row's insertion XID with FrozenTransactionId, which was visible in the row's xmin system column.")]),
  cl("On a cluster running PostgreSQL 9.3, frozen rows show up with an xmin of 2.", "on a cluster still running 9.3 frozen rows show up with an xmin of 2", S, "version_range_entailed",
     [(0, "In PostgreSQL versions before 9.4, freezing was implemented by actually replacing a row's insertion XID with FrozenTransactionId, which was visible in the row's xmin system column."), (0, "FrozenTransactionId (2)")], mode="all"),
  cl("Newer PostgreSQL versions switched to a flag bit for freezing mainly to reduce WAL volume.", "mainly to reduce WAL volume", U, "reason_substitution", [], note="The stated benefit is preserving xmin for forensic use; WAL volume is not mentioned."),
  cl("Newer PostgreSQL versions freeze rows by setting a flag bit and keep the original xmin.", "Newer versions only set a flag bit", S, "paraphrase", [(0, "Newer versions just set a flag bit, preserving the row's original xmin for possible forensic use.")]),
  cl("A cluster that was pg_upgrade'd from 9.3 can never contain rows with xmin equal to 2.", "a cluster that was pg_upgrade'd from 9.3 can never contain rows with xmin 2", C, "exception_ignored",
     [(0, "However, rows with xmin equal to FrozenTransactionId (2) may still be found in databases pg_upgrade'd from pre-9.4 versions.")]),
  cl("System catalogs can contain rows with xmin equal to 1, BootstrapTransactionId.", "System catalogs can also contain rows with xmin 1, BootstrapTransactionId", S, "paraphrase",
     [(1, "Also, system catalogs may contain rows with xmin equal to BootstrapTransactionId (1)")]),
  cl("BootstrapTransactionId is treated as older than every normal XID.", "which is treated as older than every normal XID", S, "near_verbatim", [(1, "this special XID is treated as older than every normal XID.")]),
  cl("pg_xact stores two bits of commit status per transaction.", "pg_xact stores two bits of commit status per transaction", S, "paraphrase", [(2, "The commit status uses two bits per transaction")]),
  cl("With the default horizon of 200 million transactions, pg_xact takes about 50MB.", "the default horizon of 200 million transactions costs about 50MB", S, "paraphrase",
     [(2, "(The default, 200 million transactions, translates to about 50MB of pg_xact storage and about 2GB of pg_commit_ts storage.)")]),
  cl("Raising autovacuum_freeze_max_age to its two-billion maximum would grow pg_xact to roughly 2GB.", "raising autovacuum_freeze_max_age to its two-billion maximum would grow pg_xact to roughly 2GB", C, "near_miss_number",
     [(2, "if autovacuum_freeze_max_age is set to its maximum allowed value of two billion, pg_xact can be expected to grow to about half a gigabyte")], note="2GB is the DEFAULT pg_commit_ts size; pg_xact at two billion is about half a gigabyte."),
  cl("Aggressive vacuums start running more often once multixact member storage passes about half of its roughly 20GB wraparound limit.", "aggressive vacuums start running more often once it passes about half of that", S, "arithmetic_multi_hop",
     [(6, "Also, if the storage occupied by multixacts members exceeds about 10GB, aggressive vacuum scans will occur more often for all tables"), (6, "The members storage area can grow up to about 20GB before reaching wraparound.")], mode="all", note="10GB is half of 20GB."),
  cl("XID exhaustion and MXID exhaustion both block all write transactions.", "XID exhaustion and MXID exhaustion both block all write transactions.", C, "quantifier_change",
     [(7, "XID exhaustion will block all write transactions, but MXID exhaustion will only block a subset of write transactions")]),
]})

# ---------------- R5: SQLite logic (converse refuted, contrapositive, multi-hop) ----------------
P = ["sqlite:1", "sqlite:13", "sqlite:14", "sqlite:45", "sqlite:46", "sqlite:47", "sqlite:18", "sqlite:22"]
A = ("Because the wal-index lives in shared memory, all processes using a WAL database must be on the same host, so two processes on different machines sharing a database over NFS cannot use WAL. "
     "Being on the same host, however, is enough to guarantee that WAL will work. "
     "Since there is only one WAL file, two writers can never be writing at the same moment, even though readers can run alongside a writer; this single-writer limit can be lifted with BEGIN CONCURRENT. "
     "A process can use WAL without shared memory only if it sets EXCLUSIVE locking mode before its first WAL access, and in that case it stays in EXCLUSIVE mode until it leaves WAL journal mode. "
     "With PRAGMA synchronous=NORMAL, commits skip the WAL sync and the checkpoint is the only operation that issues a sync; with FULL, every commit syncs the WAL. "
     "Running the checkpoint in a separate thread therefore guarantees that the main thread never blocks on a sync, whatever the synchronous setting.")
cases.append({"id": "reason-05-sqlite-logic", "categories": ["reasoning", "multi_passage"], "passages": P, "answer": A, "claims": [
  cl("All processes using a WAL database must be on the same host.", "all processes using a WAL database must be on the same host", S, "paraphrase",
     [(0, "All processes using a database must be on the same host computer; WAL does not work over a network filesystem.")]),
  cl("Two processes on different machines sharing a database over NFS cannot use WAL.", "two processes on different machines sharing a database over NFS cannot use WAL", S, "instantiation",
     [(0, "All processes using a database must be on the same host computer; WAL does not work over a network filesystem.")]),
  cl("Being on the same host is enough to guarantee that WAL will work.", "Being on the same host, however, is enough to guarantee that WAL will work.", C, "converse_refuted",
     [(5, "If the VFS does not support shared-memory methods, then the attempt to open a database that is already in WAL mode, or the attempt to convert a database into WAL mode, will fail.")],
     note="Necessary condition restated as sufficient; another passage gives a same-host failure case."),
  cl("Two writers can never be writing to a WAL database at the same moment.", "two writers can never be writing at the same moment", S, "paraphrase",
     [(2, "However, since there is only one WAL file, there can only be one writer at a time.")]),
  cl("In WAL mode, readers can run alongside a writer.", "readers can run alongside a writer", S, "paraphrase", [(2, "writers and readers can run at the same time")]),
  cl("SQLite's WAL single-writer limit can be lifted with BEGIN CONCURRENT.", "this single-writer limit can be lifted with BEGIN CONCURRENT", U, "extrinsic_plausible", []),
  cl("A process can use WAL without shared memory only if it sets EXCLUSIVE locking mode before its first WAL access.", "A process can use WAL without shared memory only if it sets EXCLUSIVE locking mode before its first WAL access", S, "multi_hop_necessity",
     [(3, "WAL databases can be created, read, and written even if shared memory is unavailable as long as the locking_mode is set to EXCLUSIVE before the first attempted access."),
      (5, "If NORMAL locking mode is in effect for the first WAL-mode database access, then the shared-memory wal-index is created.")], mode="all",
     note="Passage 3 gives sufficiency; passage 5 shows NORMAL-first creates the shared-memory index, giving necessity."),
  cl("A process using WAL without shared memory stays in EXCLUSIVE locking mode until it leaves WAL journal mode.", "it stays in EXCLUSIVE mode until it leaves WAL journal mode", S, "paraphrase",
     [(4, "The only way to change out of EXCLUSIVE locking mode is to first change out of WAL journal mode.")]),
  cl("With PRAGMA synchronous=NORMAL, commits skip the WAL sync.", "With PRAGMA synchronous=NORMAL, commits skip the WAL sync", S, "paraphrase",
     [(6, "(Writers sync the WAL on every transaction commit if PRAGMA synchronous is set to FULL but omit this sync if PRAGMA synchronous is set to NORMAL.)")]),
  cl("With PRAGMA synchronous=NORMAL, the checkpoint is the only operation that issues a sync.", "the checkpoint is the only operation that issues a sync", S, "paraphrase",
     [(7, "Note that with PRAGMA synchronous set to NORMAL, the checkpoint is the only operation to issue an I/O barrier or sync operation")]),
  cl("With PRAGMA synchronous=FULL, every commit syncs the WAL.", "with FULL, every commit syncs the WAL", S, "paraphrase",
     [(6, "(Writers sync the WAL on every transaction commit if PRAGMA synchronous is set to FULL but omit this sync if PRAGMA synchronous is set to NORMAL.)")]),
  cl("Running the checkpoint in a separate thread guarantees the main thread never blocks on a sync, whatever the synchronous setting.", "Running the checkpoint in a separate thread therefore guarantees that the main thread never blocks on a sync, whatever the synchronous setting.", C, "multi_hop_refutation",
     [(7, "Note that with PRAGMA synchronous set to NORMAL, the checkpoint is the only operation to issue an I/O barrier or sync operation"),
      (6, "(Writers sync the WAL on every transaction commit if PRAGMA synchronous is set to FULL but omit this sync if PRAGMA synchronous is set to NORMAL.)")], mode="all",
     note="The guarantee holds only for NORMAL; under FULL the committing thread syncs."),
]})

# ---------------- R6: Redis rewrite / versions / comparisons ----------------
P = ["redis:3", "redis:4", "redis:5", "redis:15", "redis:17", "redis:19", "redis:20", "redis:34", "redis:35", "redis:36"]
A = ("If you increment a counter 100 times, the AOF holds 100 entries even though 99 of them are unnecessary, and after a rewrite that key can be rebuilt from a single command. "
     "On Redis 2.2 you have to run BGREWRITEAOF yourself, while Redis 2.6 can trigger log rewriting automatically. "
     "Redis 2.4 and later never run an AOF rewrite and an RDB snapshot at the same time, and if you request BGREWRITEAOF while a snapshot is running, Redis schedules it and starts it once the snapshot completes. "
     "With appendfsync everysec you can lose up to one second of writes, and with appendfsync always no writes are lost in any failure scenario. "
     "RDB forks less often than AOF does. "
     "When both AOF and RDB are enabled, Redis rebuilds the dataset from the AOF on restart rather than from the RDB file.")
cases.append({"id": "reason-06-redis-rewrite-versions", "categories": ["reasoning"], "passages": P, "answer": A, "claims": [
  cl("Incrementing a counter 100 times leaves 100 entries in the AOF.", "the AOF holds 100 entries", S, "paraphrase", [(3, "but 100 entries in your AOF.")]),
  cl("99 of those 100 AOF entries are unnecessary for rebuilding the current state.", "99 of them are unnecessary", S, "paraphrase", [(3, "99 of those entries are not needed to rebuild the current state.")]),
  cl("After an AOF rewrite, that counter key can be rebuilt from a single command.", "after a rewrite that key can be rebuilt from a single command", S, "light_inference",
     [(3, "you'll end up with a single key in your dataset containing the final value"), (4, "Redis will write the shortest sequence of commands needed to rebuild the current dataset in memory.")], mode="all", contestable=True),
  cl("On Redis 2.2 you have to run BGREWRITEAOF yourself.", "On Redis 2.2 you have to run BGREWRITEAOF yourself", S, "paraphrase",
     [(4, "If you're using the AOF with Redis 2.2 you'll need to run `BGREWRITEAOF` from time to time.")]),
  cl("Redis 2.6 can trigger AOF log rewriting automatically.", "Redis 2.6 can trigger log rewriting automatically", S, "version_range_entailed", [(4, "Since Redis 2.4 is able to trigger log rewriting automatically")], note="2.6 is later than 2.4."),
  cl("Redis 2.4 and later never run an AOF rewrite and an RDB snapshot at the same time.", "Redis 2.4 and later never run an AOF rewrite and an RDB snapshot at the same time", S, "paraphrase",
     [(7, "Redis >= 2.4 makes sure to avoid triggering an AOF rewrite when an RDB snapshotting operation is already in progress, or allowing a `BGSAVE` while the AOF rewrite is in progress.")]),
  cl("If BGREWRITEAOF is requested during a snapshot, Redis schedules it and starts it once the snapshot completes.", "if you request BGREWRITEAOF while a snapshot is running, Redis schedules it and starts it once the snapshot completes", S, "paraphrase",
     [(8, "the server will reply with an OK status code telling the user the operation is scheduled, and the rewrite will start once the snapshotting is completed.")]),
  cl("With appendfsync everysec you can lose up to one second of writes.", "With appendfsync everysec you can lose up to one second of writes", S, "paraphrase", [(5, "you may lose 1 second of data if there is a disaster")]),
  cl("With appendfsync always, no writes are lost in any failure scenario.", "with appendfsync always no writes are lost in any failure scenario", U, "modality_strengthening", [], note="Docs only say 'very safe'."),
  cl("RDB forks less often than AOF does.", "RDB forks less often than AOF does.", C, "reversed_comparison", [(1, "AOF also needs to fork() but less frequently")]),
  cl("When both AOF and RDB are enabled, Redis rebuilds the dataset from the AOF on restart rather than from the RDB file.", "When both AOF and RDB are enabled, Redis rebuilds the dataset from the AOF on restart rather than from the RDB file.", S, "paraphrase",
     [(9, "the AOF file will be used to reconstruct the original dataset since it is guaranteed to be the most complete.")]),
]})

# ---------------- R7: Redis backups: counting, conditions, sufficiency ----------------
P = ["redis:39", "redis:3", "redis:4", "redis:11", "redis:19", "redis:46", "redis:47", "redis:38"]
A = ("A common backup scheme keeps hourly RDB snapshots for the latest 48 hours and daily snapshots for one or two months, which means up to 48 hourly files and as many as about 60 daily files. "
     "At least once a day a snapshot should be transferred outside the data center, or at least outside the physical machine. "
     "Redis can save the dataset every N seconds if there have been at least M changes, so with a save point of 300 seconds and 100 changes, a crash can never lose more than five minutes of writes. "
     "Snapshots sent to S3 should be encrypted, for example with gpg -c, and the password stored in several safe places. "
     "If you push backups to a VPS over SCP, verifying the file size after the transfer is enough to guarantee the backup is intact. "
     "With appendfsync no, Linux typically flushes data every 30 seconds.")
cases.append({"id": "reason-07-redis-backup-counting", "categories": ["reasoning"], "passages": P, "answer": A, "claims": [
  cl("A common backup scheme keeps hourly RDB snapshots for the latest 48 hours and daily snapshots for one or two months.", "A common backup scheme keeps hourly RDB snapshots for the latest 48 hours and daily snapshots for one or two months", S, "paraphrase",
     [(0, "you can take hourly snapshots for the latest 48 hours, and daily snapshots for one or two months.")]),
  cl("That scheme keeps up to 48 hourly snapshot files.", "up to 48 hourly files", S, "arithmetic", [(0, "you can take hourly snapshots for the latest 48 hours")]),
  cl("That scheme keeps as many as about 60 daily snapshot files.", "as many as about 60 daily files", S, "arithmetic", [(0, "and daily snapshots for one or two months.")], note="Two months is about 60 days."),
  cl("At least once a day, a snapshot should be transferred outside the data center or at least outside the physical machine.", "At least once a day a snapshot should be transferred outside the data center, or at least outside the physical machine", S, "paraphrase",
     [(0, "At least one time every day make sure to transfer an RDB snapshot *outside your data center* or at least *outside the physical machine* running your Redis instance.")]),
  cl("Redis can save the dataset every N seconds if there have been at least M changes.", "Redis can save the dataset every N seconds if there have been at least M changes", S, "paraphrase",
     [(3, "You can configure Redis to have it save the dataset every N seconds if there are at least M changes in the dataset")]),
  cl("With a save point of 300 seconds and 100 changes, a crash can never lose more than five minutes of writes.", "with a save point of 300 seconds and 100 changes, a crash can never lose more than five minutes of writes", C, "condition_reasoning",
     [(3, "You can configure Redis to have it save the dataset every N seconds if there are at least M changes in the dataset")],
     note="If fewer than 100 changes accumulate, no snapshot is taken, so the loss window can exceed five minutes.", contestable=True),
  cl("Snapshots sent to S3 should be encrypted, for example with gpg -c.", "Snapshots sent to S3 should be encrypted, for example with gpg -c", S, "paraphrase",
     [(5, "You can encrypt your data using `gpg -c` (in symmetric encryption mode).")]),
  cl("The backup encryption password should be stored in several safe places.", "the password stored in several safe places", S, "paraphrase", [(5, "Make sure to store your password in many different safe places")]),
  cl("Verifying the file size after an SCP transfer to a VPS is enough to guarantee the backup is intact.", "verifying the file size after the transfer is enough to guarantee the backup is intact", U, "sufficiency_overclaim", [],
     note="Docs recommend checking the size and possibly the SHA1 digest; they never say size alone is sufficient.", contestable=True),
  cl("With appendfsync no, Linux typically flushes data every 30 seconds.", "With appendfsync no, Linux typically flushes data every 30 seconds.", S, "paraphrase", [(4, "Normally Linux will flush data every 30 seconds with this configuration")]),
]})

# ---------------- R8: WAL-reset bug temporal reasoning ----------------
P = ["sqlite:54", "sqlite:55", "sqlite:56", "sqlite:57", "sqlite:63", "sqlite:64", "sqlite:65"]
A = ("The WAL-reset bug was found on 2026-03-03, and the fixed release, 3.51.3, came out about ten days later. "
     "The bug is likely present in releases going back to 3.7.0 from July 2010, so it went unnoticed for more than fifteen years. "
     "SQLite 3.51.2, released in January 2026, is likely affected, and the backports to 3.44.6 and 3.50.7 shipped on the same day as 3.51.3. "
     "A single-threaded application that only ever opens one connection cannot hit the bug. "
     "Because the developers could only trigger it with a special test hook, the bug has never been reproduced without modified SQLite sources. "
     "Its observed rate in the wild is no higher than the expected rate of SSD malfunctions, so unless you are doing something really unusual you are unlikely to ever encounter it.")
cases.append({"id": "reason-08-sqlite-bug-timeline", "categories": ["reasoning"], "passages": P, "answer": A, "claims": [
  cl("The WAL-reset bug was found on 2026-03-03.", "The WAL-reset bug was found on 2026-03-03", S, "near_verbatim", [(0, "On 2026-03-03, one of the SQLite developers (Dan) found and fixed a bug")]),
  cl("The fixed release 3.51.3 came out about ten days after the WAL-reset bug was found.", "the fixed release, 3.51.3, came out about ten days later", S, "temporal_arithmetic",
     [(0, "On 2026-03-03, one of the SQLite developers (Dan) found and fixed a bug"), (1, "It is fixed in version 3.51.3 (2026-03-13) and later.")], mode="all", note="2026-03-03 to 2026-03-13."),
  cl("The WAL-reset bug went unnoticed for more than fifteen years.", "it went unnoticed for more than fifteen years", S, "temporal_arithmetic",
     [(1, "The bug is likely present in all version of SQLite from 3.7.0 (2010-07-21) through 3.51.2 (2026-01-09)."), (0, "On 2026-03-03, one of the SQLite developers (Dan) found and fixed a bug")], mode="all", note="July 2010 to March 2026 is about 15.6 years."),
  cl("SQLite 3.51.2, released in January 2026, is likely affected by the WAL-reset bug.", "SQLite 3.51.2, released in January 2026, is likely affected", S, "paraphrase",
     [(1, "The bug is likely present in all version of SQLite from 3.7.0 (2010-07-21) through 3.51.2 (2026-01-09).")]),
  cl("The backports of the fix to 3.44.6 and 3.50.7 shipped on the same day as 3.51.3.", "the backports to 3.44.6 and 3.50.7 shipped on the same day as 3.51.3", U, "fabricated_detail", [], note="Backport release dates are not given."),
  cl("A single-threaded application that only ever opens one connection cannot hit the WAL-reset bug.", "A single-threaded application that only ever opens one connection cannot hit the bug.", S, "contrapositive",
     [(2, "The bug only affects databases in WAL mode when there are two or more database connections open on the same file, in separate threads or processes")]),
  cl("The WAL-reset bug has never been reproduced without modified SQLite sources.", "the bug has never been reproduced without modified SQLite sources", C, "temporal_update",
     [(5, "Phil Eaton has devised a reproducer that does not involve using the special testing code hack.")], note="Passage 4 says it was never observed without the hack; the later UPDATE (passage 5) supersedes it."),
  cl("The WAL-reset bug's observed rate in the wild is no higher than the expected rate of SSD malfunctions.", "Its observed rate in the wild is no higher than the expected rate of SSD malfunctions", S, "paraphrase",
     [(6, "the occurrence rate of this problem in the wild appears to be less than or equal to the expected occurrence rate of SSD malfunctions and/or cosmic-ray hits.")]),
  cl("Unless you are doing something really unusual, you are unlikely to ever encounter the WAL-reset bug.", "unless you are doing something really unusual you are unlikely to ever encounter it", S, "near_verbatim",
     [(6, "unless you are doing something really unusual, you are unlikely to ever encounter this problem.")]),
]})

# ---------------- R9: Redis multi-part AOF and corruption ----------------
P = ["redis:14", "redis:16", "redis:18", "redis:21", "redis:22", "redis:23", "redis:24", "redis:25", "redis:26"]
A = ("Since Redis 7.0.0 the AOF is split into at most one base file and any number of incremental files, all tracked by a manifest file that is written in JSON. "
     "During a rewrite the parent keeps writing to a newly opened incremental file, so if the rewrite fails, the old base and incremental files plus that new incremental file still represent the complete dataset. "
     "Failed rewrites are retried at a slower and slower rate. "
     "The rewrite produces a new AOF with the minimal set of operations needed to recreate the current dataset. "
     "If the AOF is merely truncated at the end, Redis loads it by default and discards the malformed last command; if it is corrupted in the middle, Redis likewise discards just the bad command and keeps going. "
     "Running redis-check-aof with --fix is always safe, because it only removes the invalid command.")
cases.append({"id": "reason-09-redis-aof-corruption", "categories": ["reasoning"], "passages": P, "answer": A, "claims": [
  cl("Since Redis 7.0.0, the AOF consists of at most one base file plus any number of incremental files.", "Since Redis 7.0.0 the AOF is split into at most one base file and any number of incremental files", S, "paraphrase",
     [(0, "the original single AOF file is split into base file (at most one) and incremental files (there may be more than one).")]),
  cl("The AOF base and incremental files are tracked by a manifest file.", "all tracked by a manifest file", S, "near_verbatim", [(0, "All these files are put in a separate directory and are tracked by a manifest file.")]),
  cl("The Redis AOF manifest file is written in JSON.", "that is written in JSON", U, "fabricated_detail", []),
  cl("During an AOF rewrite, the parent keeps writing to a newly opened incremental file.", "During a rewrite the parent keeps writing to a newly opened incremental file", S, "paraphrase",
     [(2, "the Redis parent process opens a new incremental AOF file to continue writing.")]),
  cl("If the rewrite fails, the old base and incremental files plus the newly opened incremental file still represent the complete dataset.", "if the rewrite fails, the old base and incremental files plus that new incremental file still represent the complete dataset", S, "paraphrase",
     [(7, "If the rewriting fails, the old base and increment files (if there are any) plus this newly opened increment file represent the complete updated dataset, so we are safe.")]),
  cl("Failed AOF rewrites are retried at a slower and slower rate.", "Failed rewrites are retried at a slower and slower rate.", S, "near_verbatim", [(2, "failed AOF rewrites are retried at a slower and slower rate.")]),
  cl("The AOF rewrite produces a new file with the minimal set of operations needed to recreate the current dataset.", "The rewrite produces a new AOF with the minimal set of operations needed to recreate the current dataset.", S, "paraphrase",
     [(1, "a completely new one is produced with the minimal set of operations needed to create the current data set")]),
  cl("If the AOF is only truncated at the end, Redis loads it by default and discards the malformed last command.", "If the AOF is merely truncated at the end, Redis loads it by default and discards the malformed last command", S, "paraphrase",
     [(3, "The latest major versions of Redis will be able to load the AOF anyway, just discarding the last non well formed command in the file.")]),
  cl("If the AOF is corrupted in the middle, Redis discards just the bad command and keeps going.", "if it is corrupted in the middle, Redis likewise discards just the bad command and keeps going", C, "case_confusion",
     [(5, "Redis will complain at startup and will abort:")]),
  cl("Running redis-check-aof with --fix is always safe because it only removes the invalid command.", "Running redis-check-aof with --fix is always safe, because it only removes the invalid command.", C, "exception_ignored",
     [(6, "but in that case all the AOF portion from the invalid part to the end of the file may be discarded, leading to a massive amount of data loss if the corruption happened to be in the initial part of the file.")]),
]})

# ---------------- R10: PostgreSQL ANALYZE scope ----------------
P = ["pg:10", "pg:11", "pg:12", "pg:13", "pg:14", "pg:17", "pg:18", "pg:61"]
A = ("ANALYZE gathers the statistics the query planner relies on, and it can run on its own or as an optional step in VACUUM. "
     "Because ANALYZE samples rows randomly instead of reading every row, it is usually best to just analyze the whole database; by default it samples 30,000 rows per table. "
     "The autovacuum daemon schedules ANALYZE purely as a function of the number of rows inserted or updated, so it may skip a table whose statistical distribution changed meaningfully if only a few rows were touched. "
     "Changes to partitions or inheritance children do not trigger autoanalyze on the parent table, so an inheritance parent is never analyzed by autovacuum, and autovacuum runs ANALYZE on a partitioned table only after its partitions change significantly. "
     "A timestamp column that records each row's update time will probably need more frequent statistics updates than a column of URLs.")
cases.append({"id": "reason-10-pg-analyze-scope", "categories": ["reasoning"], "passages": P, "answer": A, "claims": [
  cl("ANALYZE gathers the statistics the PostgreSQL query planner relies on.", "ANALYZE gathers the statistics the query planner relies on", S, "paraphrase",
     [(0, "These statistics are gathered by the ANALYZE command, which can be invoked by itself or as an optional step in VACUUM.")]),
  cl("ANALYZE can run on its own or as an optional step in VACUUM.", "it can run on its own or as an optional step in VACUUM", S, "paraphrase",
     [(0, "These statistics are gathered by the ANALYZE command, which can be invoked by itself or as an optional step in VACUUM.")]),
  cl("ANALYZE samples rows randomly instead of reading every row.", "ANALYZE samples rows randomly instead of reading every row", S, "paraphrase",
     [(4, "ANALYZE uses a statistically random sampling of the rows of a table rather than reading every single row.")]),
  cl("It is usually best to just analyze the whole database.", "it is usually best to just analyze the whole database", S, "near_verbatim", [(4, "In practice, however, it is usually best to just analyze the entire database, because it is a fast operation.")]),
  cl("By default, ANALYZE samples 30,000 rows per table.", "by default it samples 30,000 rows per table", U, "extrinsic_true", []),
  cl("The autovacuum daemon schedules ANALYZE purely as a function of the number of rows inserted or updated.", "The autovacuum daemon schedules ANALYZE purely as a function of the number of rows inserted or updated", S, "paraphrase",
     [(1, "The daemon schedules ANALYZE strictly as a function of the number of rows inserted or updated")]),
  cl("Autovacuum may skip ANALYZE on a table whose statistical distribution changed meaningfully if only a few rows were touched.", "it may skip a table whose statistical distribution changed meaningfully if only a few rows were touched", S, "inference_modality_weak",
     [(1, "The daemon schedules ANALYZE strictly as a function of the number of rows inserted or updated; it has no knowledge of whether that will lead to meaningful statistical changes.")]),
  cl("Changes to partitions or inheritance children do not trigger autoanalyze on the parent table.", "Changes to partitions or inheritance children do not trigger autoanalyze on the parent table", S, "paraphrase",
     [(2, "Tuples changed in partitions and inheritance children do not trigger analyze on the parent table.")]),
  cl("An inheritance parent table is never analyzed by autovacuum.", "an inheritance parent is never analyzed by autovacuum", C, "exception_ignored",
     [(6, "Inheritance parents will only be analyzed if the parent itself is changed")]),
  cl("Autovacuum runs ANALYZE on a partitioned table once its partitions change significantly.", "autovacuum runs ANALYZE on a partitioned table only after its partitions change significantly", C, "negation_flip",
     [(7, "this means that autovacuum does not run ANALYZE on partitioned tables"), (6, "The autovacuum daemon does not issue ANALYZE commands for partitioned tables.")]),
  cl("A timestamp column recording each row's update time will probably need more frequent statistics updates than a URL column.", "A timestamp column that records each row's update time will probably need more frequent statistics updates than a column of URLs.", S, "paraphrase",
     [(3, "such a column will probably need more frequent statistics updates than, say, a column containing URLs for pages accessed on a website.")]),
]})

# ---------------- R11: SQLite comparisons / transitivity ----------------
P = ["sqlite:4", "sqlite:6", "sqlite:7", "sqlite:8", "sqlite:18", "sqlite:19", "sqlite:20", "sqlite:23"]
A = ("WAL write transactions write content once instead of twice, so they are faster than rollback-journal write transactions, and checkpoints are slower than WAL write transactions. "
     "It follows that a checkpoint is also slower than a rollback-journal write transaction. "
     "For read-heavy applications, WAL might be about 1% or 2% slower than rollback mode, and WAL performs worse than rollback mode for transactions over 100 MB in every SQLite version. "
     "Read performance in WAL mode deteriorates as the WAL file grows, so for maximum read performance one would checkpoint as often as every COMMIT. "
     "In the rollback-journal approach a COMMIT happens when the journal is deleted, whereas in WAL a COMMIT happens when a commit record is appended to the WAL, so a WAL commit never has to write to the original database file.")
cases.append({"id": "reason-11-sqlite-comparisons", "categories": ["reasoning"], "passages": P, "answer": A, "claims": [
  cl("WAL write transactions write content once instead of twice.", "WAL write transactions write content once instead of twice", S, "paraphrase",
     [(4, "Write transactions are very fast since they only involve writing the content once (versus twice for rollback-journal transactions)")]),
  cl("WAL write transactions are faster than rollback-journal write transactions.", "so they are faster than rollback-journal write transactions", S, "light_inference",
     [(4, "Write transactions are very fast since they only involve writing the content once (versus twice for rollback-journal transactions)")]),
  cl("Checkpoints are slower than WAL write transactions.", "checkpoints are slower than WAL write transactions", S, "near_verbatim", [(6, "These factors combine to make checkpoints slower than write transactions.")]),
  cl("A checkpoint is slower than a rollback-journal write transaction.", "a checkpoint is also slower than a rollback-journal write transaction", U, "invalid_transitive", [],
     note="Both are slower than a WAL write; nothing orders them against each other."),
  cl("For read-heavy applications, WAL might be about 1% or 2% slower than rollback mode.", "For read-heavy applications, WAL might be about 1% or 2% slower than rollback mode", S, "paraphrase",
     [(0, "WAL might be very slightly slower (perhaps 1% or 2% slower) than the traditional rollback-journal approach in applications that do mostly reads and seldom write.")]),
  cl("WAL performs worse than rollback mode for transactions over 100 MB in every SQLite version.", "WAL performs worse than rollback mode for transactions over 100 MB in every SQLite version", C, "temporal_update",
     [(1, "Beginning with version 3.11.0 (2016-02-15), WAL mode works as efficiently with large transactions as does rollback mode.")]),
  cl("Read performance in WAL mode deteriorates as the WAL file grows.", "Read performance in WAL mode deteriorates as the WAL file grows", S, "paraphrase", [(5, "read performance deteriorates as the WAL file grows in size")]),
  cl("For maximum read performance, one would checkpoint as often as every COMMIT.", "for maximum read performance one would checkpoint as often as every COMMIT", S, "paraphrase",
     [(7, "To maximize the read performance, one wants to keep the WAL as small as possible and hence run checkpoints frequently, perhaps as often as every COMMIT.")]),
  cl("In the rollback-journal approach, a COMMIT happens when the journal is deleted.", "In the rollback-journal approach a COMMIT happens when the journal is deleted", S, "paraphrase", [(2, "The COMMIT occurs when the rollback journal is deleted.")]),
  cl("In WAL mode, a COMMIT happens when a commit record is appended to the WAL.", "in WAL a COMMIT happens when a commit record is appended to the WAL", S, "paraphrase",
     [(3, "A COMMIT occurs when a special record indicating a commit is appended to the WAL.")]),
  cl("A WAL commit never has to write to the original database file.", "a WAL commit never has to write to the original database file", S, "paraphrase",
     [(3, "Thus a COMMIT can happen without ever writing to the original database")]),
]})

spec = {"_doc": "Reasoning-focused cases. 'p' indexes this case's passages list.",
        "_guideline": json.loads(pathlib.Path("spec_hard.json").read_text())["_guideline"]
                      + " Modality/quantifier: weakening (always->can, all->some) is SUPPORTED; strengthening (typical->required, can->always) is UNSUPPORTED unless a stated exception refutes it (then CONTRADICTED). Logic: contrapositive is SUPPORTED; converse of an only-if is UNSUPPORTED, or CONTRADICTED when another passage gives a counterexample. Invalid transitive comparisons are UNSUPPORTED.",
        "sources": {"sqlite": "sqlite_wal.json", "redis": "redis_persistence.json", "pg": "pg_vacuum.json"},
        "cases": cases}
pathlib.Path("spec_reason.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1))
print(len(cases), "cases written")
