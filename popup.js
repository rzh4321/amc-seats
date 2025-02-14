document.addEventListener("DOMContentLoaded", function () {
  const seatNumberInput = document.getElementById("seatNumber");
  const checkSeatButton = document.getElementById("checkSeat");
  const submitEmailButton = document.getElementById("submitEmail");
  const messageDiv = document.getElementById("message");
  const emailSection = document.getElementById("emailSection");
  let seatingUrl;
  let showDate;
  let seatNumbers;
  let theater;
  let movie;
  let showtime;

  function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  function isValidSeatNumber(seat) {
    const pattern = /^[A-Za-z][1-9]$|^[A-Za-z]([1-4][0-9]|50)$/;
    if (!pattern.test(seat)) {
      return false;
    }

    const letter = seat.charAt(0).toUpperCase();
    return letter >= "A" && letter <= "Z";
  }

  seatNumberInput.addEventListener("input", function (e) {
    emailSection.style.display = "none";
    const rawInput = e.target.value.trim();
    const cleanInput = rawInput.endsWith(",")
      ? rawInput.slice(0, -1)
      : rawInput;

    // split into array if comma-separated, or make single item array
    seatNumbers = Array.from(
      new Set(
        cleanInput.includes(",")
          ? cleanInput.split(",").map((seat) => seat.trim().toUpperCase())
          : [cleanInput.toUpperCase()],
      ),
    );

    const invalidSeats = seatNumbers.filter((seat) => !isValidSeatNumber(seat));

    if (invalidSeats.length > 0) {
      messageDiv.textContent =
        "Each seat must be one letter (A-Z) followed by a number (1-50). Example: 'A1' or 'A1, B1, C1'";
      return;
    } else {
      messageDiv.textContent = "";
    }
  });

  checkSeatButton.addEventListener("click", function () {
    const formattedSeatNumbers = seatNumbers.map((seat) => seat.toUpperCase());

    console.log("Checking seats:", formattedSeatNumbers);

    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      const currentUrl = tabs[0].url;
      console.log("Current URL:", currentUrl);

      if (
        !currentUrl.match(
          /https:\/\/www\.amctheatres\.com\/showtimes\/.*\/seats/,
        )
      ) {
        messageDiv.textContent =
          "Please navigate to the AMC seating selection screen.";
        return;
      }
      seatingUrl = currentUrl;

      console.log("Sending message to content script...");
      chrome.tabs.sendMessage(
        tabs[0].id,
        {
          action: "checkSeat",
          seatNumbers: formattedSeatNumbers,
        },
        function (response) {
          console.log("Received response:", response);

          if (chrome.runtime.lastError) {
            console.log("Runtime error:", chrome.runtime.lastError);
            messageDiv.textContent =
              "Error: Could not communicate with the page.";
            return;
          }

          if (response.error) {
            messageDiv.textContent = response.error;
          } else {
            const {
              occupiedSeats,
              availableSeats,
              theaterName,
              movieShowtime,
              movieName,
              date,
            } = response;
            showDate = date;
            theater = theaterName;
            showtime = movieShowtime;
            movie = movieName;
            if (formattedSeatNumbers.length === 1) {
              // Single seat check
              if (occupiedSeats.length === 1) {
                messageDiv.textContent = "This seat is currently occupied.";
                emailSection.style.display = "block";
              } else {
                messageDiv.textContent = "This seat is available!";
                emailSection.style.display = "none";
              }
            } else {
              // Multiple seats check
              if (availableSeats.length > 0) {
                messageDiv.textContent = `The following seats are already available: ${availableSeats.join(", ")}`;
                emailSection.style.display = "none";
              } else {
                messageDiv.textContent =
                  "All requested seats are currently occupied.";
                emailSection.style.display = "block";
              }
            }
          }
        },
      );
    });
  });

  submitEmailButton.addEventListener("click", async function () {
    const email = document.getElementById("emailInput").value.trim();

    if (!isValidEmail(email)) {
      messageDiv.textContent = "Please enter a valid email address.";
      return;
    }

    try {
      // const response = await fetch('https://amc-seats-backend-production.up.railway.app/notifications', {

      const response = await fetch("http://localhost:8000/notifications", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          seatNumbers,
          url: seatingUrl,
          theater,
          movie,
          showtime,
          showDate: showDate.split("T")[0],
          // are_specifically_requested: false
        }),
      });

      const data = await response.json();
      if (data.error) {
        messageDiv.textContent = data.error;
        return;
      }

      if (data.exists) {
        messageDiv.textContent =
          "You're already subscribed to notifications for all these seats.";
      } else if (data.detail) {
        messageDiv.textContent = "An unknown error occurred.";
      } else {
        if (seatNumbers.length === 1) {
          messageDiv.textContent = `We'll notify ${email} when seat ${seatNumbers[0]} becomes available.`;
        } else {
          if (data.created === seatNumbers.length) {
            messageDiv.textContent = `We'll notify ${email} when any of these seats become available: ${seatNumbers.join(", ")}.`;
          } else {
            messageDiv.textContent = `Subscribed to notifications for ${data.created} new seats. Some seats were already subscribed.`;
          }
        }
        emailSection.style.display = "none";
      }
    } catch (error) {
      messageDiv.textContent = "An error occurred. Please try again later.";
      console.error("Error:", error);
    }
  });
});
