document.addEventListener("DOMContentLoaded", function () {
  const seatNumberInput = document.getElementById("seatNumber");
  const checkSeatButton = document.getElementById("checkSeat");
  const submitEmailButton = document.getElementById("submitEmail");
  const messageDiv = document.getElementById("message");
  const emailSection = document.getElementById("emailSection");
  let seatingUrl;
  let showDate;
  let seatNumbers = [];
  let theater;
  let movie;
  let showtime;
  const tabs = document.querySelectorAll(".tab");
  const tabContents = document.querySelectorAll(".tab-content");
  const checkAllSeatsButton = document.getElementById("checkAllSeats");
  const loadingDiv = document.getElementById("loading");
  let isCheckingAllSeats = false;

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tabContents.forEach((c) => c.classList.remove("active"));

      tab.classList.add("active");
      document
        .getElementById(
          tab.dataset.tab === "specific" ? "specificSeats" : "anySeats",
        )
        .classList.add("active");

      emailSection.style.display = "none";
      messageDiv.textContent = "";
      messageDiv.className = "";
    });
  });

  function showLoading() {
    loadingDiv.style.display = "block";
    checkSeatButton.disabled = true;
    submitEmailButton.disabled = true;
    checkAllSeatsButton.disabled = true;
  }

  function hideLoading() {
    loadingDiv.style.display = "none";
    checkSeatButton.disabled = false;
    submitEmailButton.disabled = false;
    checkAllSeatsButton.disabled = false;
  }

  function showMessage(text, type = "info") {
    messageDiv.textContent = text;
    messageDiv.className = type;
  }

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
        showMessage(
          "Please navigate to the AMC seating selection screen.",
          "error",
        );
        return;
      }
      seatingUrl = currentUrl;
      showLoading();
      console.log("Sending message to content script...");
      chrome.tabs.sendMessage(
        tabs[0].id,
        {
          action: "checkSeat",
          seatNumbers: formattedSeatNumbers,
        },
        function (response) {
          hideLoading();
          console.log("Received response:", response);

          if (chrome.runtime.lastError) {
            console.log("Runtime error:", chrome.runtime.lastError);
            showMessage("Error: Could not communicate with the page.", "error");
            return;
          }

          if (response.error) {
            showMessage(response.error, "error");
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
                showMessage("This seat is currently occupied.", "info");
                emailSection.style.display = "block";
              } else {
                showMessage("This seat is currently available!", "success");
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

  checkAllSeatsButton.addEventListener("click", function () {
    isCheckingAllSeats = true;
    showLoading();

    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      const currentUrl = tabs[0].url;

      if (
        !currentUrl.match(
          /https:\/\/www\.amctheatres\.com\/showtimes\/.*\/seats/,
        )
      ) {
        showMessage(
          "Please navigate to the AMC seating selection screen.",
          "error",
        );
        hideLoading();
        return;
      }

      seatingUrl = currentUrl;

      chrome.tabs.sendMessage(
        tabs[0].id,
        { action: "getAllOccupiedSeats" },
        function (response) {
          hideLoading();

          if (chrome.runtime.lastError) {
            showMessage("Error: Could not communicate with the page.", "error");
            return;
          }

          if (response.error) {
            showMessage(response.error, "error");
            return;
          }

          const { occupiedSeats, theaterName, movieShowtime, movieName, date } =
            response;

          if (occupiedSeats.length === 0) {
            showMessage("All seats are currently available!", "success");
            return;
          }

          showDate = date;
          theater = theaterName;
          showtime = movieShowtime;
          movie = movieName;
          seatNumbers = occupiedSeats;

          showMessage(
            `Found ${occupiedSeats.length} occupied seats. Enter your email to get notified when any become available.`,
            "info",
          );
          emailSection.style.display = "block";
        },
      );
    });
  });

  submitEmailButton.addEventListener("click", async function () {
    const email = document.getElementById("emailInput").value.trim();
    const activeTab = document.querySelector(".tab.active").dataset.tab;
    const isAnySeatsMode = activeTab === "any";

    if (!isValidEmail(email)) {
      showMessage("Please enter a valid email address.", "error");
      return;
    }

    showLoading();
    submitEmailButton.style;

    try {
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
          areSpecficallyRequested: !isAnySeatsMode,
        }),
      });

      hideLoading();
      const data = await response.json();

      if (data.error) {
        showMessage(data.error, "error");
        return;
      }

      if (data.exists) {
        showMessage(
          isAnySeatsMode
            ? "You're already subscribed to notifications for this showing."
            : "You're already subscribed to notifications for all these seats.",
          "info",
        );
      } else if (data.detail) {
        showMessage("An unknown error occurred.", "error");
      } else {
        let successMessage;

        if (isAnySeatsMode) {
          successMessage = `We'll notify ${email} when any seat becomes available for this showing.`;
        } else {
          if (seatNumbers.length === 1) {
            successMessage = `We'll notify ${email} when seat ${seatNumbers[0]} becomes available.`;
          } else {
            if (data.created === seatNumbers.length) {
              successMessage = `We'll notify ${email} when any of these seats become available: ${seatNumbers.join(", ")}.`;
            } else {
              successMessage = `Subscribed to notifications for ${data.created} new seats. Some seats were already subscribed.`;
            }
          }
        }

        showMessage(successMessage, "success");
        emailSection.style.display = "none";
      }
    } catch (error) {
      hideLoading();
      showMessage("An error occurred. Please try again later.", "error");
      console.error("Error:", error);
    }
  });
});

// const response = await fetch('https://amc-seats-backend-production.up.railway.app/notifications', {
