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
    results = None if len(results) == 0 else results
    print(results)
    return render_template('results.html', school_list=scraper.school_query,
                           results=results)

if __name__ == "__main__":
    app.run(ssl_context='adhoc')
