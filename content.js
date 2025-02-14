chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
  console.log("Content script received message:", request);

  if (request.action === "checkSeat") {
    console.log("Checking seats:", request.seatNumbers);
    checkSeats(request.seatNumbers).then((response) => {
      console.log("Sending response:", response);
      sendResponse(response);
    });
    return true; // Keep the message channel open for async response
  }
});

async function checkSeats(seatNumbers) {
  console.log("Starting seat check for:", seatNumbers);
  const movieInfo = document.querySelector(".headline + ul");
  const date = new Date(movieInfo.children[1].textContent);
  const theaterName = movieInfo.children[0].textContent;
  const movieShowtime = movieInfo.children[2].textContent;
  const movieName = movieInfo.previousElementSibling.textContent;

  let seatButtons = Array.from(document.getElementsByTagName("button")).filter(
    (button) => {
      const buttonText = button.textContent.trim();
      return seatNumbers.includes(buttonText);
    },
  );

  console.log("Initial seat buttons found:", seatButtons.length);

  if (seatButtons.length < seatNumbers.length) {
    const zoomInButton = document.querySelector(
      ".rounded-full.bg-gray-400.p-4",
    );
    console.log("Zoom button found:", !!zoomInButton);

    if (zoomInButton) {
      zoomInButton.click();
      console.log("Clicked zoom button");

      await new Promise((resolve) => setTimeout(resolve, 1000));

      seatButtons = Array.from(document.getElementsByTagName("button")).filter(
        (button) => seatNumbers.includes(button.textContent.trim()),
      );
      console.log("Seat buttons after zoom:", seatButtons.length);
    }

    if (seatButtons.length < seatNumbers.length) {
      return { error: "Some seat numbers were not found on this screen." };
    }
  }

  const occupiedSeats = [];
  const availableSeats = [];

  seatButtons.forEach((button) => {
    const seatNumber = button.textContent.trim();
    if (button.classList.contains("cursor-not-allowed")) {
      occupiedSeats.push(seatNumber);
    } else {
      availableSeats.push(seatNumber);
    }
  });

  return {
    occupiedSeats,
    availableSeats,
    theaterName,
    movieShowtime,
    movieName,
    date,
  };
}
