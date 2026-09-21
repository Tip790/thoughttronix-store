## Featured Product
#Question 1 - Trace the feature. Explain how marking a product as featured in the admin interface causes the badge to appear in the storefront. Explain the files involved and the code logic. 

##  Orginally the is_featured addition to the Product class didn't even add a checkbox or a badge until I asked Claude to add both to so it could appear on the website. to add the badges to the catalog and product detail listings they added a '{% if product. is_featured %}' '<span class - "badge badge-primary">Featured</span>' this follows the same code for the badge of unavailable products just the unavailable ones have 'badge-warning' instead of 'badge-primary'. These badges were added to 'catlog.html' and 'detail.html' so it could display on both sites. To display the checkbox they added 'is_featured' to the Meta class on forms.py I believe since the checkbox did not appear until it's addition.

#Question 2 - How you verified it. Describe how you confirmed the feature works. Name the pages you checked in the browser.

When I opened the browser I chechedk the edit page for a product to see if it had the is featured checkbox next to the is available one, checked it and then went to both the catalog of items and the product detail page to see if a featured badge was displayed after marking the box. I did this for all three of the items to triple check my work in case any errors occured.

#Question 3 - Judgement. Describe one challenge, unexpected result, or edge case you encountered. Explain what you did to troubleshoot it.

## My only unexpected result was the checkbox not appearing the first time the code was added as I had to cut Claude off from adding the badge too early, which probably preventing it from adding it in addition to the other changes. I troubleshooted this by asking it to make a checkbox for the website before making a badge and checking if it worked.