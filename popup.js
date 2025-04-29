document.addEventListener("DOMContentLoaded", function () {
  const seatNumberInput = document.getElementById("seatNumber");
  const checkSeatButton = document.getElementById("checkSeat");
  const specificSeatsForm = document.getElementById("specificSeats");
  const submitEmailButton = document.getElementById("submitEmail");
  const messageDiv = document.getElementById("message");
  const emailSection = document.getElementById("emailSection");
  let seatingUrl;
  let seatNumbers = [];
  let theater;
  let movie;
  let showtime;
  const tabs = document.querySelectorAll(".tab");
  const tabContents = document.querySelectorAll(".tab-content");
  const checkAllSeatsButton = document.getElementById("checkAllSeats");
  const loadingDiv = document.getElementById("loading");

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
      clearMessage();
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

  function clearMessage() {
    messageDiv.textContent = "";
    messageDiv.className = "";
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
    const rawInput = e.target.value.trim();
    let isInvalid = false;
    if (rawInput === "") {
      checkSeatButton.disabled = true;
      return;
    }
    const cleanInput = rawInput.endsWith(",")
      ? rawInput.slice(0, -1)
      : rawInput;

    // each part should be a seat number (A1), or a range of seat numbers (A1-A13)
    let parts = cleanInput.split(",").map((part) => part.trim().toUpperCase());

    let expandedSeats = [];

    parts.forEach((part) => {
      if (part.includes("-")) {
        // Handle range input like A1-A13
        const [start, end] = part.split("-").map((p) => p.trim());

        if (!isValidSeatNumber(start) || !isValidSeatNumber(end)) {
          isInvalid = true;
          return;
        }

        const startMatch = start.match(/^([A-Z])(\d{1,2})$/);
        const endMatch = end.match(/^([A-Z])(\d{1,2})$/);

        if (!startMatch || !endMatch) {
          isInvalid = true;
          return;
        }

        const [, startRow, startNumber] = startMatch;
        const [, endRow, endNumber] = endMatch;

        // Rows must match for a valid range
        if (startRow !== endRow) {
          isInvalid = true;
          return;
        }

        const startNum = parseInt(startNumber, 10);
        const endNum = parseInt(endNumber, 10);

        if (startNum > endNum || startNum <= 0 || endNum > 50) {
          isInvalid = true;
          return;
        }

        // Expand the range
        for (let i = startNum; i <= endNum; i++) {
          expandedSeats.push(`${startRow}${i}`);
        }
      } else {
        // Handle single seat input like A1
        if (!isValidSeatNumber(part)) {
          isInvalid = true;
          return;
        }
        expandedSeats.push(part);
      }
    });

    // Remove duplicates
    seatNumbers = Array.from(new Set(expandedSeats));

    if (isInvalid) {
      showMessage(
        "Each seat must be one letter (A-Z) followed by a number (1-50). Example: 'A1' or 'A1, B1, C1' or 'A1-A5'.",
        "error",
      );
      checkSeatButton.disabled = true;
      return;
    } else {
      clearMessage();
      checkSeatButton.disabled = false;
    }
  });

  specificSeatsForm.addEventListener("submit", function (e) {
    e.preventDefault();
    const formattedSeatNumbers = seatNumbers.map((seat) => seat.toUpperCase());

    console.log("Checking seats:", formattedSeatNumbers);

    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      let currentUrl = tabs[0].url;
      currentUrl = new URL(currentUrl).origin + new URL(currentUrl).pathname;

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
      chrome.tabs.sendMessage(tabs[0].id, { ping: true }, function (res) {
        if (chrome.runtime.lastError) {
          // Content script not loaded, inject it manually
          chrome.scripting.executeScript(
            {
              target: { tabId: tabs[0].id },
              files: ["content.js"],
            },
            () => {
              // Retry sending the real message after injection
              chrome.tabs.sendMessage(
                tabs[0].id,
                {
                  action: "checkSeat",
                  seatNumbers: formattedSeatNumbers,
                },
                handleResponse,
              );
            },
          );
        } else {
          // Content script already loaded, send message
          chrome.tabs.sendMessage(
            tabs[0].id,
            {
              action: "checkSeat",
              seatNumbers: formattedSeatNumbers,
            },
            handleResponse,
          );
        }
      });
    });
  
    function handleResponse(response) {
      hideLoading();
      console.log("Received response:", response);
    
      if (chrome.runtime.lastError) {
        console.log("Runtime error:", chrome.runtime.lastError);
        showMessage(
          "Error: If you are currently on the seating map, try refreshing the page.",
          "error",
        );
        return;
      }
    
      if (response.error) {
        showMessage(response.error, "error");
      } else {
        const { occupiedSeats, availableSeats, theaterName, movieName, date } =
          response;
        theater = theaterName;
        showtime = date;
        movie = movieName;
        seatNumbers = occupiedSeats;
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
            showMessage(
              `The following seats are already available: ${availableSeats.join(", ")}`,
              "success",
            );
            emailSection.style.display = "none";
          } else {
            showMessage("All requested seats are currently occupied.");
            emailSection.style.display = "block";
          }
        }
      }
    }
  
  }



);


  checkAllSeatsButton.addEventListener("click", function () {
    isCheckingAllSeats = true;
    showLoading();

    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      let currentUrl = tabs[0].url;
      currentUrl = new URL(currentUrl).origin + new URL(currentUrl).pathname;

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

          const { occupiedSeats, theaterName, movieName, date } = response;

          if (occupiedSeats.length === 0) {
            showMessage("All seats are currently available!", "success");
            return;
          }

          theater = theaterName;
          showtime = date;
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
      const response = await fetch(
        "https://amc-seats-backend-production.up.railway.app/notifications",
        {
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
            areSpecficallyRequested: !isAnySeatsMode,
          }),
        },
      );

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
