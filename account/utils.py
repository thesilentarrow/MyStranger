from django.core.serializers.python import Serializer


class LazyAccountEncoder(Serializer):
    def get_dump_object(self, obj):
        dump_object = {}
        dump_object.update({'id': str(obj.id)})
        dump_object.update({'email': str(obj.email)})
        dump_object.update({'name': str(obj.name)})
        dump_object.update({'uniName': str(obj.university_name)})
        # dump_object.update({'uni_name': str(obj.universityName)})
        return dump_object
    

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
