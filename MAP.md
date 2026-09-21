#The apps and what each owns. Four apps, one or two sentences each.

##  Their are four apps: accounts, products, orders, and dashboard.  Account owns the idenitity as in who is signing in from customer to employee. Where they seperate between 'is_staff' and 'is_superuser' to seperate the permissions granted. products owns the catalog as it is what shows the search methods and whather products are available. Orders owns everything from cart to fufilled order and is what maintains the order list, order history, and the transaction status. Finally the dashboard owns the staf analytivs page that you get when you sign in as an employee.

#The path of one request. From browser to rendered page for the home page /, naming the files: the URL pattern, the view, and the template.

## Django starts at 'config/urls.py' on the 10th line, scrolling down the 'urlpatterns' until it finds the Url to match with, for this example it will be 'product.urls' once it matches it looks for all the other url matches, eventually finding the view 'products/views.py'.  After that it goes to the template products/catalog.html and and renders the page, it's extensions, and the badges in base.html to show them all on the Django website.

#A model you read. Pick the Cart or User model from Step 6. In one or two sentences, say what it represents and name one method or field in it that was new or interesting to you.

## Cart is a model that that represents objects added or removed from the customer's cart as they begin the process of purchasing item/s. The method that stood out to me is the 'settings.AUTH_USER_MODEL as it is used to keep the ordered items from hard locking themselves to a certain user model, pairing with the 'on_delete=models.CASCADE' ti take the cart along with a user if it was deleted.

#Deleting a category. Products belong to categories through a ForeignKey. State what happens to a category's products when the category is deleted, and name the line of code that decides.

## Attempting to delete the category will not delete the product as the catergory function in 'products/models.py' has an 'on_delete=models.PROTECT' which prevents the category and products from being deleted.

#Where the tests live. How the suite is organized and what conftest.py provides.

## The tests are stored in the accounts/tests.py products/tests.py prodcuts/test_backoffice.py orders/tests.py orders/test_orders.py orders/test_services.py orders/test_checkout_form.py orders/test_validators.py orders/test_backoffice.py and finally dashboard/tests.py. The suite is organized into fixtures  like conftest which calls on all the different files and runs their tests by requesting the function arguements withn the fixture. This allows these tests to be ran all together despite being in different files in the overall folder. 

#One thing you're still working to understand. Name one part of this codebase you do not fully understand yet. If everything is clear, name the part that took the most work to understand. Then describe what you did to get a handle on it: a follow-up you asked the agent, a file you opened, a small test you ran. Say where you ended up. You do not lose points for still being unsure. This section grades the attempt, not whether you solved it.

##Seeing as there is a wide variety of new code I had asked Claude to decribe the transaction term used when exploring the deep module but I'm not sure if I really understand that at all. As it described that it basically treats a group of writes as one singular write that require all to pass to prevent errors in the database. Looking it up on google doesn't really have an answer either as I'm not sure Transaction code is the same as the transaction being described here. Other than that I should've asked more about the slugs throughout the project as it was mentioned when I asked it how it would prevent having products of the same name. 