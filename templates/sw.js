// // const urlBase64ToUint8Array = base64String => {
// //     const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
// //     const base64 = (base64String + padding)
// //         .replace(/\-/g, '+')
// //         .replace(/_/g, '/');

// //     const rawData = atob(base64);
// //     const outputArray = new Uint8Array(rawData.length);

// //     for (let i = 0; i < rawData.length; ++i) {
// //         outputArray[i] = rawData.charCodeAt(i);
// //     }

// //     return outputArray;
// // }

// // const saveSubscription = async (subscription) => {
// //     // Here i am sending the subscription details to backend to store it in my database and getting back the response

// // }

// // self.addEventListener("activate", async (e) => {
// //     const subscription = await self.registration.pushManager.subscribe({
// //         userVisibleOnly: true,
// //         applicationServerKey: urlBase64ToUint8Array("YOUR_PUBLIC_KEY")
// //     })

// //     const response = await saveSubscription(subscription)
// //     console.log(response)
// // })

// // self.addEventListener("push", e => {
// //     self.registration.showNotification("Wohoo!!", { body: e.data.text() })
// // })


// // Register event listener for the 'push' event.
// self.addEventListener('push', function (event) {
//     console.log('bc call ni karo moey')
//     // Retrieve the textual payload from event.data (a PushMessageData object).
//     // Other formats are supported (ArrayBuffer, Blob, JSON), check out the documentation
//     // on https://developer.mozilla.org/en-US/docs/Web/API/PushMessageData.
//     const eventInfo = event.data.text();
//     const data = JSON.parse(eventInfo);
//     const head = data.head || 'New Notification 🕺🕺';
//     const body = data.body || 'This is default content. Your notification didn\'t have one 🙄🙄';

//     // Keep the service worker alive until the notification is created.
//     event.waitUntil(
//         self.registration.showNotification(head, {
//             body: body,
//             icon: 'https://i.imgur.com/MZM3K5w.png'
//         })
//     );
// });

{% comment %} console.log('sw rocks')
self.addEventListener('fetch', function(event) {}); {% endcomment %}
