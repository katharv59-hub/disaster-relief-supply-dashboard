/* ========================= */
/* DYNAMIC BAR CHART */
/* ========================= */

/* GET DATA FROM FLASK */

const cities =
JSON.parse(
document.getElementById("cityData").textContent
);

const stocks =
JSON.parse(
document.getElementById("stockData").textContent
);


/* CREATE BAR CHART */

const ctx =
document.getElementById("barChart");

new Chart(ctx, {

type: "bar",

data: {

labels: cities,

datasets: [{

label: "Current Stock",

data: stocks,

borderWidth: 1

}]

},

options: {

responsive: true,

maintainAspectRatio: false,

scales: {

y: {

beginAtZero: true

}

}

}

});