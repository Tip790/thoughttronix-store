## Product Images

##Question 1 - One decision from grill me. Choose one '/grill-me' question that led to an important design decision. If you disagreed with the agent's recommendation, explain what it recommended, why you rejected that recommendation, what you chose instead, and how your choice affected the feature. If you did not disagree with any recommendation, choose a question that was confusing. Explain what you did not understand, the follow-up question(s) you asked, and how you ultimately decided.

# The only decision I really disagreed with was its recomendation on which image to use for the SynchRest product. It wanted to use the one without text to make it look cleaner on the website, but I felt that the text added much more significant context to the item compared to just a woman sleeping on a pillow. This effected the outcome by having it prioritize making the text a little more readable which ended up helping all of the images be more legible on the website.

##Question 2 - Find the upload code. 1. Find the 'ImageField' the agent added to the Product model. Copy that line into your answer and include the filename and line number. Explain what the upload_to value does.
2.Find the <form> used to upload a product image. Copy the opening <form> tag into your answer and include the filename and line number. Explain why enctype is needed for a file upload.

#1. 'products/models.py' line 78 'image = models.ImageField(upload_to="products/", blank=True)' 'upload_to' determines the storage directory and filename for the image being uploaded, in this case 'products/'. This works with the 'MEDIA_ROOT' setting to find where exactly to upload the 'image' files to their respective products.
#2. 'products/templates/products/manage_product_form.html' line 13 '<form method="post" enctype="multipart/form-data" class="mt-2 space-y-4">' enctype tells the browser that the '<form>' contains filedata because the default cannot handle large files or binary data needed to upload the images we needed. Without the enctype the file would upload incorrectly as images are not plain text.

##Question 3 - Follow the upload process. Your invented product's image is stored somewhere on disk and served from some URL. Follow the image for the product you created through the application and write:

The path where the image file is stored on disk.
The value stored in the database for that image.
The URL the browser requests to display it.
For each one, name the Django field or setting that determines it and the file where that field or setting is defined. Finally, explain what code makes the media URL work while you run the development server. If you cannot find one of these, ask the agent, check the code, confirm your understanding, and write it up in your own words.

-'MEDIA_ROOT = BASE_DIR/ "media" in config/settings.py' line 146 + the value in the database which is 'products/Carpet_Ai_Art.webp' which relative to the project root is 'media/products/Carpet_Ai_Art/webp'. 
- The value is stored in the database db.sqlite3 at it's project root 'config/settings.py' line 85-90. Which adds it to the database as the value 'products/Carpet_Ai_Art.webp.
- 'Media_URL = media/' at 'config/settings.py' line 144. Uses the / after media to show the value is relative, then the product image uses 'upload_to="products/"' from 'products/models.py line 78' to store the file as       '/media/products/Carpet_Ai_Art/webp' which is what's shown in the database. This turns into the above URL which is then served in 'config/urls.py' line 28 but only if the 'DEBUG=True' 

## Featured Product
#Question 1 - Trace the feature. Explain how marking a product as featured in the admin interface causes the badge to appear in the storefront. Explain the files involved and the code logic. 

##  Orginally the is_featured addition to the Product class didn't even add a checkbox or a badge until I asked Claude to add both to so it could appear on the website. to add the badges to the catalog and product detail listings they added a '{% if product. is_featured %}' '<span class - "badge badge-primary">Featured</span>' this follows the same code for the badge of unavailable products just the unavailable ones have 'badge-warning' instead of 'badge-primary'. These badges were added to 'catlog.html' and 'detail.html' so it could display on both sites. To display the checkbox they added 'is_featured' to the Meta class on forms.py I believe since the checkbox did not appear until it's addition.

#Question 2 - How you verified it. Describe how you confirmed the feature works. Name the pages you checked in the browser.

When I opened the browser I chechedk the edit page for a product to see if it had the is featured checkbox next to the is available one, checked it and then went to both the catalog of items and the product detail page to see if a featured badge was displayed after marking the box. I did this for all three of the items to triple check my work in case any errors occured.

#Question 3 - Judgement. Describe one challenge, unexpected result, or edge case you encountered. Explain what you did to troubleshoot it.

## My only unexpected result was the checkbox not appearing the first time the code was added as I had to cut Claude off from adding the badge too early, which probably preventing it from adding it in addition to the other changes. I troubleshooted this by asking it to make a checkbox for the website before making a badge and checking if it worked.

## Discount Coupons

#Question 1 - One decision from grill me. Choose one /grill-me question that led to an important design decision. If you disagreed with the agent's recommendation, explain what it recommended, why you rejected that recommendation, what you chose instead, and how your choice affected the feature. If you did not disagree with any recommendation, choose a question that was confusing. Explain what you did not understand, the follow-up question(s) you asked, and how you ultimately decided.

## I think the decision that helped was rejecting the idea of keeping the discount codes invisible on Q16 of the 'prompts.md' folder. I did this because I feel websites typically do show things like discounts for items and a badge giving the coupon out makes sense for this small scale project, and so it could display which specfic products were discounted. Rather than relying on the customer to magically know what the codes were. This made it so two of the Seraphine line items now have a badge displaying that you can get 50% off by using the code SERAPHINE50. This code is also shown in a previous order and was used after the discount was retired.

#Question 2 - The change. Explain the change you made after reviewing the feature. Describe your original choice, what the browser showed you, why you wanted to change it, and how the fix works. If any existing test failed during your build, name it and say what you did about it.

## The change I made was adding a much more noticeable pop-up for when a discount fails during checkout. Orginally it appeared next to the price's at the top of the page, which would require someone to scroll up from the checkout button just to see why their price did not change. Now, the screen has a pop-up that you click "Try another Code" or "Continue without Code" so it is much more noticeable to the customer. I don't believe any test failed but I know Ruff had some formatting issues the agent had to fix three different times. Also at the end they used a '--force tailwind build' which didn't impact the website at all and the code seems to still work. Though It's hard not to worry when AI is known to hallucinate.