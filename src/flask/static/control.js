// function to handle form submission
function submitForm(){
    var priceRangeLow = document.getElementById('priceRangeLow').value;
    var priceRangeHigh = document.getElementById('priceRangeHigh').value;
    var numberOfGrids = document.getElementById('numberOfGrids').value;
    var margin = document.getElementById('margin').value;

    //Use Fetch API to send the request
    fetch('/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({priceRangeLow: priceRangeLow, 
            priceRangeHigh: priceRangeHigh,
            numberOfGrids: numberOfGrids,
            margin: margin 
        }),
    })
    .then(response => response.json())  // Parse the JSON response
    .then(data => {
        // Display the response message in the HTML
        document.getElementById('response').innerText = data.message;
    })
    .catch(error => {
        console.error('Error:', error);
    })
}

// Function to fetch data when button is clicked
function getOrderHistory(){
    console.log('111')
    fetch('/order_history')  // This URL would be the API endpoint
        .then(response => response.json())  // Convert the response to JSON
        .then(data => {
            // Display the fetched data in the paragraph
            document.getElementById('response').innerText = JSON.stringify(data);
        })
        .catch(error => {
            console.error('Error:', error);
        });
}
