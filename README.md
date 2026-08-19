# Zara Stock Tracker

A Python-based application that monitors product availability on Zara Turkey and sends Telegram notifications when tracked products become available.

## Project Overview

This project automates the process of monitoring Zara product pages.

The application uses Selenium to access Zara product pages, checks product availability, and sends notifications through Telegram when a tracked product is detected as available.

A desktop interface is also included for managing the tracking process.

## Features

- Monitor Zara product pages
- Check product availability automatically
- Track multiple products
- Send Telegram notifications
- Desktop GUI built with CustomTkinter
- Automated Chrome WebDriver management
- Store tracking data locally in JSON format
- Periodic background checking

## Application Interface
<p align="center">
  <img src="https://github.com/user-attachments/assets/52b8062b-a5a1-4c92-b49d-133ae35806c4" width="450">
</p>


## Technologies

- Python
- Selenium
- CustomTkinter
- Requests
- Telegram Bot API
- WebDriver Manager
- JSON
- Threading

## Project Structure

```text
zara-stock-tracker/
├── zara_takip.py
├── requirements.txt
├── .gitignore
├── README.md
└── zara_tracker.png
```

## Installation

Clone the repository:

```bash
git clone https://github.com/serracelikk/zara_stock_tracker.git
cd zara_stock_tracker
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```
