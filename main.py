# Importing necessary libraries
import requests  # For HTTP requests
from selenium import webdriver  # For browser automation
from selenium.webdriver.common.by import By  # For locating elements in Selenium
from bs4 import BeautifulSoup  # For parsing HTML content
import time  # For time-related functions
import nltk  # Natural Language Toolkit for text processing
from selenium.webdriver.chrome.options import Options  # For configuring Chrome options in Selenium
from selenium.webdriver.chrome.service import Service as ChromeService  # For setting up Chrome driver service
from flask import Flask, jsonify, request  # Flask for web application, jsonify for JSON responses
from nltk.sentiment import SentimentIntensityAnalyzer  # For sentiment analysis
import argparse  # For parsing command line arguments
import os

# Constants and global variables
RATE_LIMIT = 0.1  # Rate limit for making HTTP requests (in seconds)
LAST_REQUEST = time.time()  # Time of the last request
index_url = 'https://www.ign.com/news'
articles_to_fetch = 10

# Setting up a Flask application
app = Flask(__name__)

# Configuring Chrome options for Selenium WebDriver
options = webdriver.ChromeOptions()
options.headless = True  # Enable headless mode for Chrome
options.add_argument('--headless')  # Argument for headless mode
options.add_argument('--no-sandbox')  # Argument to disable the sandbox for Chrome
options.add_argument('--disable-dev-shm-usage')  # Argument to disable /dev/shm usage

# Downloading the VADER lexicon for sentiment analysis
nltk.download('vader_lexicon')
# Creating an instance of SentimentIntensityAnalyzer for sentiment analysis
sia = SentimentIntensityAnalyzer()

# Setting up the Chrome WebDriver service
service = ChromeService(executable_path='/usr/local/bin/chromedriver')
# Creating a Chrome WebDriver instance with the specified service and options
driver = webdriver.Chrome(service=service, options=options)

# HTTP headers to use for requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}


def rate_limited_request(url):
    global LAST_REQUEST
    # Calculate the time passed since the last request
    time_since_last_request = time.time() - LAST_REQUEST
    # If the time passed is less than the rate limit, wait for the difference
    if time_since_last_request < RATE_LIMIT:
        time.sleep(RATE_LIMIT - time_since_last_request)
    # Make the HTTP request with the specified headers
    response = requests.get(url, headers=headers)
    # Update the time of the last request to the current time
    LAST_REQUEST = time.time()
    # Return the response object
    return response

def count_words(text):
    # Split the text into words based on spaces
    words = text.split()
    # Return the number of words
    return len(words)
    
def get_blog_post_content_and_sentiment(url):
    # Make a rate-limited request to the given URL
    response = rate_limited_request(url)
    # Check if the HTTP request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content of the response
        soup = BeautifulSoup(response.content, 'html.parser')
        # Find the content within a section with class 'article-page'
        content = soup.find('section', class_='article-page')
        # If content is found, extract the text and analyze its sentiment
        if content:
            text_content = content.get_text(strip=True)
            # Use the SentimentIntensityAnalyzer to get the sentiment score
            sentiment_score = sia.polarity_scores(text_content)['compound']
            # Return the text content and the sentiment score
            return text_content, sentiment_score
    else:
        # If the HTTP request failed, print the error
        print(f'Failed to fetch {url}: HTTP {response.status_code}')
    # Return None and 0 if no content is found or if an error occurred
    return None, 0



def get_article_urls(index_url, articles_to_fetch, game_name):
    # Open the index URL using Selenium WebDriver
    driver.get(index_url)
    
    # Retrieve the initial scroll height of the webpage
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    # Continue scrolling down until the desired number of articles is found or no more new content loads
    while len(driver.find_elements(By.CSS_SELECTOR, "a[href^='/articles/']")) < articles_to_fetch:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)  # Wait for the page to load new content

        # Get the new scroll height after loading new content
        new_height = driver.execute_script("return document.body.scrollHeight")
        # If the scroll height hasn't changed, break the loop (no more content to load)
        if new_height == last_height:
            break
        last_height = new_height
    
    # Get the page source from the browser after scrolling
    page_source = driver.page_source
    # Use BeautifulSoup to parse the page source
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # Find all <a> tags that potentially contain article links
    article_links = soup.find_all('a', href=True)

    # Base URL for constructing the full article URLs
    base_url = 'https://www.ign.com'
    game_related_urls = []  # List to store filtered URLs
    
    # Iterate through each article link
    for link in article_links:
        # Check if the href attribute of the link starts with '/articles/'
        if link['href'].startswith('/articles/'):
            # Find the <span> tag with class 'item-title' which contains the article title
            title_span = link.find('span', class_='item-title')
            # If the span is found and contains the game name, add the URL to the list
            if title_span and game_name.lower() in title_span.get_text(strip=True).lower():
                full_url = base_url + link['href']  # Construct the full URL
                game_related_urls.append(full_url)  # Append to the list of URLs
    
    # Return the list of URLs, limited to the specified number of articles
    return game_related_urls[:articles_to_fetch]

# List of game names to analyze
game_names = [
    "Baldur's Gate",
    "Mortal Kombat",
    "Call of Duty",
    "Mario Kart",
    "Hogwarts Legacy",
    "Grand Theft Auto",
    "Cities: Skylines"
]


def analyze_game_articles(game_name):
    article_urls = get_article_urls(index_url, articles_to_fetch, game_name)
    if not article_urls:
        return None  # Return None if no articles are found

    total_words = 0
    total_sentiment_score = 0
    for url in article_urls:
        content, sentiment = get_blog_post_content_and_sentiment(url)
        if content:
            total_words += count_words(content)
            total_sentiment_score += sentiment

    # Calculating averages
    average_word_count = total_words / len(article_urls) if article_urls else 0
    average_sentiment_score = total_sentiment_score / len(article_urls) if article_urls else 0

    return average_word_count, average_sentiment_score


@app.route('/analyze/<game_name>', methods=['GET'])
def get_game_analysis(game_name):
    if game_name not in game_names:
        return jsonify({'error': 'Game not found'}), 404

    results = analyze_game_articles(game_name)
    if results is None:
        return jsonify({'error': 'No articles found'}), 404

    average_word_count, average_sentiment_score = results
    return jsonify({
        'game': game_name,
        'average_word_count': average_word_count,
        'average_sentiment_score': average_sentiment_score
    })

if __name__ == "__main__":
    # Cloud Run sets the PORT environment variable to tell your application
    # which port to listen on.
    port = int(os.environ.get("PORT", 8080))  # Default to 8080 if not specified
    app.run(debug=True, host='0.0.0.0', port=port)


# List to store results for each game
results = []