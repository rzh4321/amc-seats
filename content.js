chrome.runtime.onMessage.addListener(function (request, sender, sendResponse) {
  console.log("Content script received message:", request);

  if (request.action === "checkSeat") {
    console.log("Checking seats:", request.seatNumbers);
    checkSeats(request.seatNumbers).then((response) => {
      sendResponse(response);
    });
    return true;
  } else if (request.action === "getAllOccupiedSeats") {
    getAllOccupiedSeats().then(sendResponse);
    return true;
  }
});

function getMovieInfo() {
  const movieInfo = document.querySelector(".headline + ul");
  const dateText = movieInfo.children[1].textContent;
  const timeText = movieInfo.children[2].textContent;
  const theaterName = movieInfo.children[0].textContent;
  const movieName = movieInfo.previousElementSibling.textContent;

  // Convert "Today, February 16, 2025" or "Thursday, February 16, 2025" to a Date
  const cleanDateText = dateText.replace(
    /^(Today|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), /,
    "",
  );

  // Combine date and time
  const dateTimeStr = `${cleanDateText} ${timeText}`;

  const date = new Date(dateTimeStr);

  const isoString = date.toISOString();

  return {
    date: isoString,
    theaterName,
    movieName,
  };
}
async function checkSeats(seatNumbers) {
  console.log("Starting seat check for:", seatNumbers);
  const { date, theaterName, movieName } = getMovieInfo();

  let seatButtons = Array.from(document.getElementsByTagName("button")).filter(
    (button) => {
      const buttonText = button.textContent.trim();
      return seatNumbers.includes(buttonText);
    },
  );

  if (seatButtons.length < seatNumbers.length) {
    const zoomInButton = document.querySelector(
      ".rounded-full.bg-gray-400.p-4",
    );

    if (zoomInButton) {
      zoomInButton.click();

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
    movieName,
    date,
  };
}

async function getAllOccupiedSeats() {
  const { date, theaterName, movieName } = getMovieInfo();
  // try to find seat buttons
  let seatButtons = Array.from(document.getElementsByTagName("button")).filter(
    (button) => button.textContent.trim().match(/^[A-Z][0-9]+$/),
  );

  // If we don't find many seats, try zooming in
  if (seatButtons.length < 5) {
    const zoomInButton = document.querySelector(
      ".rounded-full.bg-gray-400.p-4",
    );
    if (zoomInButton) {
      zoomInButton.click();
      await new Promise((resolve) => setTimeout(resolve, 1000));

      seatButtons = Array.from(document.getElementsByTagName("button")).filter(
        (button) => button.textContent.trim().match(/^[A-Z][0-9]+$/),
      );
    }
  }

  const occupiedSeats = seatButtons
    .filter((button) => button.classList.contains("cursor-not-allowed"))
    .map((button) => button.textContent.trim());

  return {
    occupiedSeats,
    theaterName,
    date,
    movieName,
  };
}
