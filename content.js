chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    console.log('Content script received message:', request);
    
    if (request.action === "checkSeat") {
      console.log('Checking seat:', request.seatNumber);
      checkSeat(request.seatNumber).then(response => {
        console.log('Sending response:', response);
        sendResponse(response);
      });
      return true; // Keep the message channel open for async response
    }
  });
  
  async function checkSeat(seatNumber) {
    console.log('Starting seat check for:', seatNumber);
    const movieInfo = document.querySelector('.headline + ul');
    date = new Date(movieInfo.children[1].textContent);
    
    let seatButtons = Array.from(document.getElementsByTagName('button')).filter(button => {
      const buttonText = button.textContent.trim();
      console.log('Found button with text:', buttonText);
      return buttonText === seatNumber;
    });
  
    console.log('Initial seat buttons found:', seatButtons.length);
  
    if (seatButtons.length === 0) {
      const zoomInButton = document.querySelector(".rounded-full.bg-gray-400.p-4");
      console.log('Zoom button found:', !!zoomInButton);
      
      if (zoomInButton) {
        zoomInButton.click();
        console.log('Clicked zoom button');
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        seatButtons = Array.from(document.getElementsByTagName('button')).filter(button => 
          button.textContent.trim() === seatNumber
        );
        console.log('Seat buttons after zoom:', seatButtons.length);
      }
  
      if (seatButtons.length === 0) {
        return { error: "Seat number not found on this screen." };
      }
    }
  
    const seatButton = seatButtons[0];
    const isOccupied = seatButton.classList.contains('cursor-not-allowed');
    console.log('Seat occupied status:', isOccupied);
  
    return { isOccupied, date };
  }