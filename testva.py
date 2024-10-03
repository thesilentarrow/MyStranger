# # email1 = "samurai@ninja.edu"
# # email2 = "samurai@ninja.edu.in"
# # email3 = "samurai@ninja.ac.in"
# # college_email = email3.split('.')[-1:]
# # print(college_email)
# # if not (college_email == ['edu']):
# #     college_email = email3.split('.')[-2:]
# #     print(college_email)
# #     if not (college_email == ['edu', 'in'] or college_email == ['ac', 'in']):
# #         print("not allowed")
# from mystranger_app.utils import haversine_distance, calculate_distance

# lat1 = 28.3671232
# lon1 = 77.54045993787369

# lat2 = '30.353478703235428'
# lon2 = '76.36329004517'



# distance =  haversine_distance(lat1, lon1, lat2, lon2)
# # distance =  calculate_distance(lat1, lon1, lat2, lon2)
# print(f"The distance between the two locations is {distance:.2f} kilometers.")

def extract_name(email):
    # Split the email address at '@' to get the local part
    local_part = email.split('@')[0]

    # Check if there is a dot in the local part
    if '.' in local_part:
        # Split the local part at dots
        parts = local_part.split('.')
        
        # Check each part to find the first string
        for part in parts:
            if not part.isdigit():
                # Found the first string, capitalize the first letter and return
                return part.capitalize()
    
    # If no dot or string found, use the entire local part as the name and capitalize the first letter
    return local_part.capitalize()

# # Example usage:
# email_address = "2020508.jadu@gu.edu.in"
# name = extract_name(email_address)
# print("Extracted Name:", name)


# Example usage:
# email_address = "2020508.jadu@gu.edu.in"
# email_address = "himanshu.20scse1010431@galgotiasuniversity.edu.in"
email_address = "2234.akash.3344.singh@gcollege.edu"
name = extract_name(email_address)
print("Extracted Name:", name)
