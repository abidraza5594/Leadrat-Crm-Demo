/* Country selection and numbering rules come from intl-tel-input/libphonenumber. */
window.BeaconPhoneField = function(input, error) {
  function showError(message) {
    error.textContent=message;error.hidden=!message;
    input.setCustomValidity(message);input.setAttribute('aria-invalid',String(!!message));
  }
  const iti=window.intlTelInput(input, {
    initialCountry:'in', separateDialCode:true, countrySearch:true,
    dropdownParent:document.body,
    loadUtils:()=>import('/vendor/intl-tel-input/js/utils.js')
  });
  // Keep an unavailable asset from becoming an unhandled rejection.
  let loadError=false;iti.promise.catch(()=>{loadError=true;});
  const clear=()=>showError('');
  input.addEventListener('input',clear);
  input.addEventListener('countrychange',clear);
  input.addEventListener('invalid',()=>{
    if(input.validity.valueMissing)showError('Enter your phone number.');
  });
  return {
    showError,
    async getNumber() {
      try {await iti.promise;} catch {loadError=true;}
      if(loadError){showError('Phone validation could not load. Refresh the page and try again.');return null;}
      if(!iti.isValidNumber()) {
        const country=iti.getSelectedCountry();
        showError('Enter a valid phone number for '+(country?.name || 'the selected country')+'.');
        input.focus();return null;
      }
      clear();return iti.getNumber();
    }
  };
};
