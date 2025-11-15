sudo chmod +x /opt/dailysync/run_daily_check.sh

File: /etc/systemd/system/dailysync-daily-check.service

[Unit]
Description=Daily standup compliance check

[Service]
Type=oneshot
Environment="APP_BASE_URL=https://your-app-domain"
Environment="INTERNAL_API_KEY=your-super-secret-key"
ExecStart=/opt/dailysync/run_daily_check.sh

File: /etc/systemd/system/dailysync-daily-check.timer

[Unit]
Description=Run daily standup compliance check once per day

[Timer]
OnCalendar=*-*-* 12:05:00
Persistent=true

[Install]
WantedBy=timers.target


sudo systemctl daemon-reload
sudo systemctl enable dailysync-daily-check.timer
sudo systemctl start dailysync-daily-check.timer

# Check status
systemctl status dailysync-daily-check.timer
systemctl status dailysync-daily-check.service
journalctl -u dailysync-daily-check.service --since today


sudo chmod +x /opt/dailysync/run_daily_check.sh

File: /etc/systemd/system/dailysync-weekly-report.service
[Unit]
Description=Weekly standup summary report

[Service]
Type=oneshot
Environment="APP_BASE_URL=https://your-app-domain"
Environment="INTERNAL_API_KEY=your-super-secret-key"
ExecStart=/opt/dailysync/run_weekly_report.sh


File: /etc/systemd/system/dailysync-weekly-report.timer
[Unit]
Description=Run weekly standup report every Friday evening

[Timer]
OnCalendar=Fri 18:05:00
Persistent=true

[Install]
WantedBy=timers.target

sudo systemctl daemon-reload
sudo systemctl enable dailysync-weekly-report.timer
sudo systemctl start dailysync-weekly-report.timer

systemctl status dailysync-weekly-report.timer
journalctl -u dailysync-weekly-report.service --since "last Friday"