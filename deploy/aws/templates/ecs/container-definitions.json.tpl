[
    {
        "name": "gooctoplusbot-api",
        "image": "${app_image}",
        "essential": true,
        "memoryReservation": 256,
        "environment": [
            {"name": "POSTGRES_HOST", "value": "${db_host}"},
            {"name": "POSTGRES_DB", "value": "gooctoplusdemo"},
            {"name": "POSTGRES_USER", "value": "${db_user}"},
            {"name": "POSTGRES_PASSWORD", "value": "${db_pass}"},
            {"name": "POSTGRES_PORT", "value": "5432"},
            {"name": "SLACK_APP_TOKEN", "value": "xapp-1-A060Z82T1B2-6012755772356-31755c2da392c3d28c672015e537a98a9181e62a20f0790302dfc2f8773a697b"},
            {"name": "SLACK_BOT_TOKEN", "value": "xoxb-5935286290582-6007380382181-srGq1RiGNBM1g9dppSfQOYqV"},
            {"name": "SLACK_USER_TOKEN", "value": "xoxp-5935286290582-5927394664007-6012753386884-f6e98364a3167d1a501b4bbd21752614"},
            {"name": "PAGERDUTY_API_TOKEN", "value": "u+X42VLEoXtxzQV7ThPg"},
            {"name": "PAGERDUTY_API_USERNAME", "value": "apd1@gooctoplus.com"},
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