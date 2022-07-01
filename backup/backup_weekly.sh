find /data/backup_ap_nimbus/weekly/ -name "*.gz" -type f -mtime +91 -delete
docker run --rm --net ap_nimbus_network --user postgres --env-file /data/backup_ap_nimbus/env.backup postgres:14.1-bullseye pg_dump | gzip > /data/backup_ap_nimbus/weekly/django_ap_nimbus_client-$(date +%d-%m-%Y).gz
tar -zcf /data/backup_ap_nimbus/weekly/uploaded_files_and_logs-$(date +%d-%m-%Y).tar.gz --absolute-names /data/docker/volumes/ap_nimbus_file_upload/_data/
