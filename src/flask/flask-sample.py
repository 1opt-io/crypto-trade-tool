# python 3.9.20
from flask import Flask, request, jsonify

app = Flask(__name__,static_url_path='') 

@app.route('/submit', methods=['POST'])
def submit_config():
    # Get JSON data from the request
    data = request.get_json()
    priceRangeLow = data.get('priceRangeLow')
    priceRangeHigh = data.get('priceRangeHigh')
    numberOfGrids = data.get('numberOfGrids')
    margin = data.get('margin')
    # Return a JSON response with a custom message
    response = {"message": f"Price Range: {priceRangeLow} - {priceRangeHigh}, \nNumber of Grids: {numberOfGrids}, \nMargin: {margin}, \nsuccessfully submitted!"}
    return jsonify(response)



@app.route('/order_history', methods=['GET'])
def get_order_history():
    data = {"message": "This is a request for order history"}
    print(data)
    return jsonify(data)


#homepage
@app.route('/')
def homepage():
    return app.send_static_file('homepage.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='127.0.0.1')