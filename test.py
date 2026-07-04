html = """
<div class="product">
  <h2>Product Title</h2>
  <div class="price">
    <span class="discount">12.99</span>
    <span class="full">19.99</span>
  </div>
  <div class="price">
    <span class="discount">13.11</span>
    <span class="full">29.33</span>
  </div>
</div>
"""
from bs4 import BeautifulSoup

soup = BeautifulSoup(html)
product = {
    "title": soup.find(class_="product").find("h2").text,
    "full_price": soup.find(class_="product").find_all(class_="full").text,
    "price": soup.select_one(".price .discount").text,
}
print(product)
