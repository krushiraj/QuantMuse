module.exports = {
  apps: [
    {
      name: 'paper-trading-api',
      script: 'scripts/run_api.py',
      interpreter: '/Users/krushi/Documents/github/QuantMuse/venv/bin/python',
      cwd: '/Users/krushi/Documents/github/QuantMuse',
      env: {
        PYTHONPATH: '/Users/krushi/Documents/github/QuantMuse',
        PYTHONUNBUFFERED: '1'
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      error_file: '/Users/krushi/Documents/github/QuantMuse/logs/api-error.log',
      out_file: '/Users/krushi/Documents/github/QuantMuse/logs/api-out.log',
      merge_logs: true
    },
    {
      name: 'paper-trading-scheduler',
      script: 'scripts/run_scheduler.py',
      args: '--session-id 2 --market both',
      interpreter: '/Users/krushi/Documents/github/QuantMuse/venv/bin/python',
      cwd: '/Users/krushi/Documents/github/QuantMuse',
      env: {
        PYTHONPATH: '/Users/krushi/Documents/github/QuantMuse',
        PYTHONUNBUFFERED: '1'
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      error_file: '/Users/krushi/Documents/github/QuantMuse/logs/scheduler-error.log',
      out_file: '/Users/krushi/Documents/github/QuantMuse/logs/scheduler-out.log',
      merge_logs: true
    }
  ]
};
