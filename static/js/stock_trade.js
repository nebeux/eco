document.getElementById('sharesInput').addEventListener('input', function() {
  const total = (parseFloat(this.value) || 0) * PRICE;
  document.getElementById('totalVal').textContent = '$' + total.toFixed(2);
});
 
document.querySelector('.buy-action').addEventListener('click', function() {
  const shares = parseFloat(document.getElementById('sharesInput').value);
  if (!shares || shares <= 0) return alert('Enter a valid number of shares.');
  fetch('/api/buy', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({symbol: SYMBOL, shares: shares, price: PRICE})
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) return alert(data.error);
    alert(`Bought ${shares} share(s) of ${SYMBOL} for $${(shares * PRICE).toFixed(2)}`);
    document.getElementById('nav-balance').textContent = '$' + data.new_balance.toFixed(2);
  });
});
 
document.querySelector('.sell-action').addEventListener('click', function() {
  const shares = parseFloat(document.getElementById('sharesInput').value);
  if (!shares || shares <= 0) return alert('Enter a valid number of shares.');
  fetch('/api/sell', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({symbol: SYMBOL, shares: shares, price: PRICE})
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) return alert(data.error);
    alert(`Sold ${shares} share(s) of ${SYMBOL} for $${(shares * PRICE).toFixed(2)}`);
    document.getElementById('nav-balance').textContent = '$' + data.new_balance.toFixed(2);
  });
});