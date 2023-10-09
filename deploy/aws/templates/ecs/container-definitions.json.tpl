[
    {
        "name": "gooctoplusbot-api",
        "image": "${app_image}",
        "essential": true,
        "memoryReservation": 256,
        "environment": [
            {"name": "POSTGRES_HOST", "value": "${db_host}"},
            {"name": "POSTGRES_DB", "value": "${db_name}"},
            {"name": "POSTGRES_USER", "value": "${db_user}"},
            {"name": "POSTGRES_PASSWORD", "value": "${db_pass}"},
            {"name": "POSTGRES_PORT", "value": "5432"},
            {"name": "SLACK_APP_TOKEN", "value": "xapp-1-A05TSBC6N04-5941847473587-1804752414e4d328fecf58726e2d476f0b51dbdb849b2f87ba53c781b877ef94"},
            {"name": "SLACK_BOT_TOKEN", "value": "xoxb-5935286290582-5939013383509-lyxi54JzTzCQyMTY7yV9xBzC"},
            {"name": "SLACK_USER_TOKEN", "value": "xoxp-5935286290582-5927394664007-5954575675985-ebe04d55b4ae5e9fe7e0c985834b2041"},
            {"name": "PAGERDUTY_API_TOKEN", "value": "u+ND4ivwQMgsxsCJns5A"},
            {"name": "PAGERDUTY_API_USERNAME", "value": "aman@gooctoplus.com"},
            {"name": "STATUSPAGE_API_KEY", "value": "ef3a8f8ae5bb44e88bf4c667978a0990"},
            {"name": "STATUSPAGE_PAGE_ID", "value": "0cqcvf2hnt1h"},
            {"name": "STATUSPAGE_URL", "value": "https://gooctoplus1.statuspage.io/"},
            {"name": "ATLASSIAN_API_URL", "value": "https://gooctoplus.atlassian.net"},
            {"name": "ATLASSIAN_API_USERNAME", "value": "aman@gooctoplus.com"},
            {"name": "ATLASSIAN_API_TOKEN", "value": "ATATT3xFfGF0RpOE83XSdS9x-70jNzdJT13pCa7_oURmn-2UT0P7jQ2aukD8y0L-mMNQ3qzhUmfZuI-Gdu9tLeUJrbLNn3xLClfLGKl7Ue23JsXpoOxXxtQTKf-gL5LxkSDvdF-Teohyl54ull_h6x1vOJazYXgw-nnGnajBGAOPBtDxyMj--xM=0E97FCBD"},
            {"name": "DEFAULT_WEB_ADMIN_PASSWORD", "value": "foobar1234"},
            {"name": "FLASK_APP_SECRET_KEY", "value": "supersecret"},
            {"name": "JWT_SECRET_KEY", "value": "supersecret"},
            {"name": "ZOOM_ACCOUNT_ID", "value": "-9Ez02bfTRqOsHrIsgqYuA"},
            {"name": "ZOOM_CLIENT_ID", "value": "T8SeCEQzRxK9g6g_BZ9WQ"},
            {"name": "ZOOM_CLIENT_SECRET", "value": "z4xTMQilgkgYo06f7V97b891lm4KeozF"},
            {"name": "CHATGPT_API_KEY", "value": "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"}
        ],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": "${log_group_name}",
                "awslogs-region": "${log_group_region}",
                "awslogs-stream-prefix": "api"
            }
        },
        "portMappings": [
            {
                "containerPort": 3000,
                "hostPort": 3000
            }
        ],
        "mountPoints": [
            {
                "readOnly": false,
                "containerPath": "/vol/web",
                "sourceVolume": "static"
            }
        ]
    }
]