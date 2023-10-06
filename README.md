# California DMV Appointment Availability Tracker
## Introduction
I had to find an appointment at the DMV for my behind-the-wheel test, but available dates were months away (as of August 2023). In order to catch any canceled appointments, I wrote a script to check for available appointments periodically and send me a notification via Telegram if there is one. I was able to find an appointment within a day of running the script.

## Screenshot
![Screenshot of Telegram notification](./docs/screenshots/telegram.png)

## Usage
1. Set up configuration constants by opening `bot.py`
2. Install the required packages using `pip install -r requirements.txt`
3. Run the script using `python bot.py`

## Notes
- This script will NOT create appointments for you. It will only notify you if there is an available appointment. You will have to book the appointment yourself.
- Choose a reasonable lookup interval, so that you don't DoS the API endpoint.
- There were some ghost appointments that were not actually available when I tried to book them.
- Currently, the script includes branch codes for some SF Bay Area DMVs. To add a different branch, you would have to extract it by inspecting the network traffic that the DMV website makes when you search for appointments.
- This script was written in few hours, so it is not very robust or sophisticated, but it got the job done. It may break if the DMV endpoint changes.

## Disclaimer
This script is for educational purposes only (again, it will NOT create an appointment for you). I am not responsible for any misuse of this script. Please use responsibly.

## License
GPLv3