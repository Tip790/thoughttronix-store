##Product Reviews

##Question 1 - Review TDD. Choose one phase where /tdd was used. Identify one behavior selected for TDD and explain why it was a good candidate for TDD. Then explain what the test checked and how a passing test provided evidence that the behavior worked. Name the test is your response.

# The TDD option I'm choosing is Phase 6's 'def test_list_shows_product_reviewer_rating_and_excerpt' in line 135-147 of '@reviews/test_backoffice.py' this test asserts wheather the backoffice tab properly displayed the reviews listed. This is a good candidate for TDD as if this test didn't pass, the reviews wouldn't display in the backoffice at all with all of the details for employees to look through and edit if they choose. This test is using it's asserts to prove that each review has an attached reviewer: 'assert "Mira K." in html', product: 'assert product.name in html', rating: 'assert "3★" in html' and their comments in the review 'assert "A" * 79 + "…" in html + assert "A" * 200 not in html'. When these tests pass, it means at least one review in the back office exists that contains the necessary atrributes needed for when an employee wishes to edit or delete a review. Meaning it contains the name, product, rating, and comment all within the /backoffice/review/ tab instead of a employee needing to track each review down personally.

##Question 2 - Trace an authorization rule. Find the code that deletes a review. Identify the exact view or function that handles the request and explain how the code determines whether the current user is allowed to perform the action. Reference filenames and line numbers in your response.

# Well to first begin we have to find where the user gets that permission and that is from class OwnReviewView in lines 68-82 of @reviews/views/py. 
'def own_review(self, pk):
        product = get_object_or_404(Product, pk=pk)
        review = Review.objects.filter(user=self.request.user, product=product)
        return product, review.first()' 
this displays the review if the user is the owner of the review using the .request.user. this shows up on the delete request in line 126 'class ReviewDeleteConfirmView(OwnReviewView):' Which checks if the author of the review 'own_review=review' wants to delete the review. This is later confirmed in line 136 'class ReviewDeleteView(OwnReviewView):' which uses 'review = self.own_review(pk) (line 141) to check if the author is the primary creator of the review, then they use 'review.delete()' (line 143) to remove the review and returns the empty review slot space back in case a new review needs to be written in 'return render_slot(request, product, oob_summary=True) (line 144).

##Question 3 - Trace one HTMX interaction. Choose the meaningful HTMX interaction you added. Identify the template containing the hx-post attribute, the URL that receives the request, the view that handles it, and the HTML or partial returned by Django. Explain which part of the page HTMX replaces and what the user sees after the request completes. Reference filenames and line numbers in your response.

# Most of the HTMX interactions added were for the buttons, the one I am choosing is 
    '<button type="button" class="btn btn-error btn-sm"
                hx-post="{% url 'reviews:delete' product.pk %}"
                hx-target="#review-author-slot" hx-swap="outerHTML">Yes, delete</button>' 
located in '@templates/reviews/partials/_review_card.html' line 25-27 this is essentially the button that displays when you are confirming whether to delete a review. The hx-post sends us to @reviews/urls.py line 13-17:
    'path(
        "reviews/<int:pk>/delete/confirm/",
        views.ReviewDeleteConfirmView.as_view(),
        name="delete_confirm",
    ),'
This url leads us to the ReviewDeleteConfirmView in '@reviews/views.py' line 126: 
'class ReviewDeleteConfirmView(OwnReviewView):
    """The author's card in its "Delete this review?" state."""

    def get(self, request, pk):
        product, review = self.own_review(pk)
        if review is None:
            return render_slot(request, product)
        return render_slot(request, product, slot="confirm_delete", own_review=review)'
mentioned in a previous question, this is the double check if the author wishes to delete their review if they select the new hx-swap button "Yes, Delete" it will move on to delete the review. From the websites perspective when you click the "Delete" button on your review the site will double check with you, cuasing the button to HX-Swap to "Yes, Delete" and a new button appears if you wish to cancel. This is what the HTMX is replacing as the actual deletion process is donw through a different view and url.

##Question 4 - One design decision from grill-me. Choose one design decision from your interview that required you to choose between reasonable options. Explain the options, the decision you made, and one tradeoff you accepted. Then identify where that decision appears in your PRD or completed code.

#I would say Q5: 'reviews only on the product detail page, with a "★ 4.3 · 12 reviews" summary line' in line 479-480 of the PROMPTS.md section. This is because it made the reviews only show up on the product detail page over having stars show up on the catalog with their products. That is what I orginally wanted, but when it mentioned the tradeoffs and increased coding needed to put it in I decided against it, running the pytest is already taking about three minutes to do so avoiding adding more code is the better option to make sure I am not overloading the project. Though, this means customers cannot check the product's rating at a glance and need to click on the product to see how reccomended it is. Though this is not a significant trade-off, it can be annoying for some customers. This shows up on the PRD at line 19 which states that the Reviews section is added to every product's detail page instead of detail page + star rating on catalog like I orginally planned.

##Account Security Center

##Question 1 - Review one phase. Choose one phase from plans/account-security.md. What working behavior was supposed to exist at the end of that phase? Explain how you verified it in the browser and what you observed before you approved the next phase. If you found a problem, explain the correction. If it worked the first time, explain the evidence you used to approve it.

# Phase 3 is the phase I'm choosing, it's behavior was to "email" the user if they forgot their password and follow a link to change it, pairing with a previous phase it would also make the account verified as well. I orginally struggled with this as I could not find the link to open the "forgot password" site to verify that the password could actually change, luckily I realized the "email" on the terminal contained the link and verifyied that you could change your password using a link, this change would verify the account and unknown emails would not receive the forgot password email, seeing the tests and verification pass I moved to the next phase. No problems came up but in the 'PROMPTS.md' it shows I asked it how to find the links as I didn't realize how too, the same issue is prevlaent in the 'PROMPTS.md' for the next phase but I resolved that too.

##Question 2 - Authentication code versus the lesson. Reopen Understanding Authentication. Identify two Django authentication components used in your completed Account Security Center. For each component, name the exact file where it appears, describe or quote the relevant line of code, and explain what the component does. Then explain how the implementation matches the authentication pattern from the lesson.

#  There are two change from the Lesson within the first thing covered, the User Model at '@account/models.py line 68-83. These changes were done in the grill-me to check email verification and that deleted users are anonymized without deleting the order history from the backend. line 77 'ANONYMIZED_USERNAME_PREFIX = "deleted-user-"' is used whenever the user deletes their account but have made previous orders that should remain on the backend, this is done so we are not holding privacy data that we no longer have access too as they are no longer a User of our website. This is also shown with the code on line 83 'email_verified = models.BooleanField(default=False)' this makes all default verifications false for the numerous user emails on the database. This is so we can use the email verification links and that customers can verify their emails since this feature was newly added and customers may not have emails associated with their accounts. This matches the pattern in the lesson as it adds additonal behaviors to the standard user that is then used for all the other inherited users.

##Question 3 - Password management versus the lesson. Reopen Password Management. Choose either password change or password reset from your implementation. Name the exact file where the important code appears and identify the Django-provided view, form, function, or other password component it uses. Explain what that component does and how your implementation compares with the pattern from the lesson. If the implementation differs in a meaningful way, explain why you accepted the difference or what you changed.

# '@accounts/urls.py pg 34-47 these contain the PasswordReset views as shown in the Password Management chapter, which are used to accept the reset(PasswordResetRequestView), confirm that the instructions were actually requested (PasswordResetDoneView), validates the new password and the link sent to the requestor (PasswordResetConfirmView) and the final step shown PasswordResetCompleteView was ommited, this and the usage of PasswordResetRequestView with PasswordResetView included in the view at '@account/views.py' differ from the Password Management section. I believe this is because when working theough the grill-me the agent and I agreed to use .env if the app was deployed, however I realized this could've probably been a mistake as I did remind the agent we are not using actual emails, we agreed to leave the code in case deployment actually happens and I believe the difference is because of that decision. This also is reflected in Phase 7 as it focuses only on things that effect the code if the website was deployed. I didn't see a need to change it as it fufills the same purpose in the testing.

##Question 4 - The tracer-bullet plan. Look back at plans/account-security.md. Choose one phase and explain why it was a useful stopping point. What working behavior existed when the phase was complete, and how did that make the feature easier to review before moving on?

# Phase 4 was merged together when I ran the prd-to-plan skill as I believed it would be better to combine both the change email and change password phases together. This made it to where we could test changing everything all at once instead of seperately and compressed the phases from 9 to 7 so we didn't have too many sessions. This was one of the most important phases as well since the ability to change your password or email is crucial if you wanted to use the website but for any reason had to change one/both of those two options. After the phase was complete you can change your password and email from the newly created Account tab on the website instead of only being able to change it from the admin site. This made the rest of the features easy to test as we couldn't really completely do Phase 5's hardening process without these sections being made first. Since testing throttling on data that doesn't exist is impossible.

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