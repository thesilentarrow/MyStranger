
// // Import the Firebase scripts using importScripts
// // If you do not serve/host your project using Firebase Hosting see https://firebase.google.com/docs/web/setup
// importScripts('/__/firebase/9.2.0/firebase-app-compat.js');
// importScripts('/__/firebase/9.2.0/firebase-messaging-compat.js');
// importScripts('/__/firebase/init.js');
// // Initialize Firebase
// const firebaseConfig = {
//     apiKey: "AIzaSyDyNyMD0b0BHTzMj-mULfQW9qc2lwh6CmU",
//     authDomain: "mystranger4.firebaseapp.com",
//     projectId: "mystranger4",
//     storageBucket: "mystranger4.appspot.com",
//     messagingSenderId: "547419092017",
//     appId: "1:547419092017:web:3db968cbd00da61eff9110",
//     measurementId: "G-3HZ2RQV1PT"
//   };
  

// firebase.initializeApp(firebaseConfig);


// // Retrieve an instance of Firebase Messaging so that it can handle background messages
// const messaging = firebase.messaging();

// messaging.onMessage(res=>{
//         console.log('got the notif baby -',res)
//     })


// // Handle background messages
// messaging.onBackgroundMessage(payload => {
//   console.log('[firebase-messaging-sw.js] Received background message ', payload);
//   // Customize notification here
//   const notificationTitle = payload.notification.title;
//   const notificationOptions = {
//     body: payload.notification.body,
//     icon: '/firebase-logo.png'
//   };

//   self.registration.showNotification(notificationTitle, notificationOptions);
// });


// Import the necessary Firebase modules
// Import the Firebase scripts
importScripts('https://www.gstatic.com/firebasejs/8.6.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.6.1/firebase-messaging.js');

// Your Firebase configuration object
const firebaseConfig = {
    apiKey: "AIzaSyDyNyMD0b0BHTzMj-mULfQW9qc2lwh6CmU",
    authDomain: "mystranger4.firebaseapp.com",
    projectId: "mystranger4",
    storageBucket: "mystranger4.appspot.com",
    messagingSenderId: "547419092017",
    appId: "1:547419092017:web:3db968cbd00da61eff9110",
    measurementId: "G-3HZ2RQV1PT"
};
// Initialize Firebase
firebase.initializeApp(firebaseConfig);


console.log('atleast i got called')

// Initialize Firebase Cloud Messaging
const messaging = firebase.messaging();


  
  // // Handle background messages
  // messaging.setBackgroundMessageHandler(function(payload) {
  //   console.log('Received background message ', payload);
  //   // Customize notification here
  //   var notificationTitle = payload.title;
  //   var notificationOptions = {
  //     body: payload.body,
  //     icon: '/firebase-logo.png',
  //     data: {
  //       // Put your data here
  //       url: payload.data.url
  //     }
  //   };
  
  //   return self.registration.showNotification(notificationTitle,
  //     notificationOptions);
  // });

//   self.addEventListener('push', function(event) {
//     var data = event.data.json();
//     var tag = data.data.tag;
//     var url = data.data.url;
//     var logo = data.data.logo;
//     var body = data.notification.body;

//     event.waitUntil(
//         self.registration.showNotification(data.notification.title, {
//             body: body,
//             icon: logo,
//             tag: tag,
//             data: {
//                 url: url
//             }
//         })
//     );
// });



  // Handle notification click
self.addEventListener('notificationclick', (event) => {
  // Close the notification
  event.notification.close();

  // Get the URL to redirect to
  const urlToRedirect = event.notification.data.url;

  // Open the specific URL in a new window/tab
  event.waitUntil(clients.openWindow(urlToRedirect));
});
// messaging.onMessage(payload => {
//     console.log("Message received. ", payload);
//     const { title,...options } = payload.notification;
//   });

//   messaging.onBackgroundMessage(function (payload) {
//     const notification = payload.notification;
//     const options = {
//       body: notification.body,
//       icon: notification.icon,
//     //   sound: "/media/notification.mp3",
//     };
//     // const audio = new Audio("/media/notification.mp3");
//     // audio.play();
//     return self.registration.showNotification(payload.notification.title, options);
//   });
  