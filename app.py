from flask import Flask, render_template, request
from SDNScraper import SDNScraper

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/results', methods=['POST'])
def results():
    assert request.method == 'POST'
    data = request.form
    scraper = SDNScraper(data)
    results = scraper.scrape()
    for dict in results:
        for message, date in dict.items():
            print(f"Date: {date}")
            print(f"Message: {message}")
    return render_template('results.html', school_list=scraper.school_query,
                           results=results)

@app.route('/error')
def error():
    return render_template('error.html')

if __name__ == "__main__":
    app.run()
