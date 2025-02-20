# CA DMV Appointment Bot

A Discord bot that monitors California DMV appointment availability and notifies you when earlier dates become available.

## Features

- Monitors multiple DMV locations (currently Redwood City and San Mateo)
- Sends notifications via Discord webhook
- Configurable check intervals
- Automatic retries on API failures
- Rate limiting handling
- Detailed logging

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```bash
cp .env.example .env
```

4. Edit `.env` with your Discord webhook URL and preferences:
```
DISCORD_WEBHOOK_URL=your_webhook_url_here
FIND_DATES_BEFORE=2025-02-27
LOOKUP_INTERVAL_SEC=600
```

## Running Locally

```bash
python discord_bot.py
```

## Docker Deployment

Build the container:
```bash
docker build -t dmv-bot .
```

Run the container:
```bash
docker run -d --env-file .env dmv-bot
```

## Project Structure

```
.
├── discord_bot.py     # Main bot script
├── requirements.txt   # Python dependencies
├── Dockerfile        # Docker configuration
├── .env.example     # Example environment variables
└── README.md        # This file
```

## Error Handling

The bot includes:
- Automatic retries for failed requests
- Exponential backoff
- Detailed error logging
- Discord notifications for critical errors

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.
