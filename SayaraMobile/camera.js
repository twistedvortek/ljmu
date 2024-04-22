const video = document.getElementById('video');

function startCamera() {
  const camera = localStorage.getItem('selectedCamera');
  const constraints = {
    video: { facingMode: (camera === 'user' ? 'user' : 'environment') }
  };

  navigator.mediaDevices.getUserMedia(constraints)
    .then(function(stream) {
      video.srcObject = stream;
    })
    .catch(function(error) {
      console.error("Error accessing the camera: ", error);
      alert("An error occurred while accessing the camera. Please check camera permissions.");
    });
}

window.onload = startCamera;
