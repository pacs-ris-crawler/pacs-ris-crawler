# Installation of Apache Solr

Solr 7.7 is the production core. Solr 10 can be initialized separately on port 8984.

## Steps (Solr 7.7)
* Install solr
* Create a core with `solr create -c <core-name>`
* Run `bash upload-schema.sh <core-name> <port>` for a new core
* On an existing core, add echo instance fields without a full reindex: `bash modify-schema.sh <core-name> <port>`

## Steps (Solr 10)
* Start Solr 10 in **user-managed (standalone)** mode. Solr 10 `bin/solr start` defaults to SolrCloud; that is what produces `coreNodeName missing` on core CREATE.

  ```bash
  sudo /opt/solr-10.0.0/bin/solr stop -p 8984
  sudo /opt/solr-10.0.0/bin/solr start --user-managed -p 8984
  ```

  Do not pass `-c` / `--cloud`. Confirm with `curl -sS "http://localhost:8984/solr/admin/info/system?wt=json"` — `mode` must be `std`, not `solrcloud`.
* Optional data location: set `SOLR_DATA_HOME=/var/www/solr10_data` in `solr.in.sh` (directory owned by the Solr user), then restart. Prefer that over a CREATE `dataDir` outside Solr home.
* Create the core and upload the schema: `bash init-solr10.sh [core-name] [port] [dataDir]`
  (defaults: `pacs_crawler` `8984`; `dataDir` is optional and only used when the core is created)
* The script also removes `_nest_path_` so `[child parentFilter=Category:parent]` works like Solr 7. Leave that field in place only if you switch the app to Solr 8+ named nested docs.
* A custom `dataDir` outside Solr home needs a JVM allow-list on the Solr host, then a restart:
  `SOLR_OPTS="$SOLR_OPTS -Dsolr.security.allow.paths=/var/www/solr10_data"`
  in `solr.in.sh`. The directory must exist and be writable by the Solr user.
