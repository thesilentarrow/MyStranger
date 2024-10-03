# MyStranger.in

Welcome to the GitHub repository of **MyStranger.in**, MyStranger.in is a Djnago based social networking site that helps you to connect with nearby college students anonymously. It provides you an exclusive community of college students within 60 km of your college.

![Static Badge](https://img.shields.io/badge/10%2C000%2B-Unique_Site_Visits-Blue)
![Static Badge](https://img.shields.io/badge/13%2C00%2B-Registered_Users-blue)

### Features

- **Omegle like Random Connect**: Users can randomly connect with other nearby college students using the text/video feature.
- **Facebook like Features**: Users can see & create posts within their exclusive nearby college's community and can add each other as friend and can chat with each other.
- **Blind Dates**: Users can go on blind dates with other nearby college students. 

We ensure that only college students can join the site by using the .edu-verification system.

## Technical Details

### Tech Stack

- HTML
- CSS
- JavaScript
- Django with Channels
- PostgreSQL
- Redis
- WebRTC
- Mapbox API

### Key Implementations

- **Peer-to-Peer Connection**: Leveraged WebRTC technology and STUN servers to facilitate an Omegle-like video chat feature, enabling real-time, anonymous interactions among users.
- **Real-Time Messaging**: Utilized Django Channels to construct a dynamic messaging section, similar to Facebook’s messaging system, allowing instantaneous text communication.
- **Multi-Layered Comment Section**: Implemented a multi-layered comment section using the Modified Preorder Tree Traversal (MPTT) data structure in Django, enhancing user engagement and interaction.
- **Location-Based Search**: Integrated the Mapbox API to enable a map search functionality, allowing users to fetch their university and connect with students based on university locations.

We hope you find this repository useful for understanding the workings of MyStranger.in. Feel free to explore the code and contribute!
