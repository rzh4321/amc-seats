document.addEventListener('DOMContentLoaded', function() {
    const checkSeatButton = document.getElementById('checkSeat');
    const submitEmailButton = document.getElementById('submitEmail');
    const messageDiv = document.getElementById('message');
    const emailSection = document.getElementById('emailSection');
    let seatingUrl;

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
        return letter >= 'A' && letter <= 'Z';
      }
    
  
    checkSeatButton.addEventListener('click', function() {
        const seatNumber = document.getElementById('seatNumber').value.trim();
    
        if (!isValidSeatNumber(seatNumber)) {
          messageDiv.textContent = "Please enter a valid seat number (e.g., 'A1'). Must be one letter (A-Z) followed by a number (1-50).";
          return;
        }
    
        const formattedSeatNumber = seatNumber.toUpperCase();
        
        console.log('Checking seat:', formattedSeatNumber); // Debug log
    
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
          console.log('Current tab:', tabs[0]); // Debug log
          
          const currentUrl = tabs[0].url;
          console.log('Current URL:', currentUrl); // Debug log
          
          if (!currentUrl.match(/https:\/\/www\.amctheatres\.com\/showtimes\/.*\/seats/)) {
              messageDiv.textContent = "Please navigate to the AMC seating selection screen.";
              return;
            }
          seatingUrl = currentUrl;
    
          console.log('Sending message to content script...');
          chrome.tabs.sendMessage(tabs[0].id, {
            action: "checkSeat",
            seatNumber: formattedSeatNumber
          }, function(response) {
            console.log('Received response:', response);
            
            if (chrome.runtime.lastError) {
              console.log('Runtime error:', chrome.runtime.lastError);
              messageDiv.textContent = "Error: Could not communicate with the page.";
              return;
            }
    
            if (response.error) {
              messageDiv.textContent = response.error;
            } else if (response.isOccupied) {
              messageDiv.textContent = "This seat is currently occupied.";
              emailSection.style.display = "block";
            } else {
              messageDiv.textContent = "This seat is available!";
              emailSection.style.display = "none";
            }
          });
        });
      });
  
    submitEmailButton.addEventListener('click', async function() {
        const email = document.getElementById('emailInput').value.trim();
        const seatNumber = document.getElementById('seatNumber').value.trim().toUpperCase();
        
        if (!isValidEmail(email)) {
          messageDiv.textContent = "Please enter a valid email address.";
          return;
        }

        console.log(JSON.stringify({
            email: email,
            seatNumber: seatNumber,
            pageUrl: seatingUrl
          }))
      
        // try {
        //     const response = await fetch('https://your-api-domain.com/notifications', {
        //       method: 'POST',
        //       headers: {
        //         'Content-Type': 'application/json',
        //       },
        //       body: JSON.stringify({
        //         email: email,
        //         seatNumber: seatNumber,
        //         pageUrl: seatingUrl
        //       })
        //     });
      
        //     const data = await response.json();
            
        //     if (data.exists) {
        //       messageDiv.textContent = "You're already subscribed to notifications for this seat.";
        //     } else {
        //       messageDiv.textContent = `We'll notify ${email} when seat ${seatNumber} becomes available.`;
        //       emailSection.style.display = "none";
        //     }
        //   } catch (error) {
        //     messageDiv.textContent = "An error occurred. Please try again later.";
        //     console.error('Error:', error);
        //   }
        });
  });