import os
from decimal import Decimal
import simplejson as json
from security import safe_requests


class RatesNotAvailableError(Exception):
    """
    Custom exception when https://theforexapi.com is down and not available for currency rates
    """
    pass


class DecimalFloatMismatchError(Exception):
    """
    A float has been supplied when force_decimal was set to True
    """
    pass


class Common:

    def __init__(self, force_decimal=False):
        """"""
        
        self._force_decimal = force_decimal

    def _source_url(self):
        """"""
        
        return "https://theforexapi.com/api/"

    def _get_date_string(self, date_obj):
        """"""
        
        if date_obj is None:
            return 'latest'
        date_str = date_obj.strftime('%Y-%m-%d')
        return date_str

    def _decode_rates(self, response, use_decimal=False, date_str=None):
        """"""
        
        if self._force_decimal or use_decimal:
            decoded_data = json.loads(response.text, use_decimal=True)
        else:
            decoded_data = response.json()
        # if (date_str and date_str != 'latest' and date_str != decoded_data.get('date')):
        #     raise RatesNotAvailableError("Currency Rates Source Not Ready")
        return decoded_data.get('rates', {})

    def _get_decoded_rate(
            self, response, dest_cur, use_decimal=False, date_str=None):
        """"""
        
        return self._decode_rates(
            response, use_decimal=use_decimal, date_str=date_str).get(
            dest_cur, None)


class CurrencyRates(Common):

    def get_rates(self, base_cur, date_obj=None):
        """Gets currency rates from a specified source.
        Parameters:
            - base_cur (str): The base currency for the rates.
            - date_obj (datetime): The date for which the rates are requested. If not specified, the current date is used.
        Returns:
            - dict: A dictionary containing the currency rates for the specified base currency and date.
        Processing Logic:
            - Uses the specified base currency and date to construct a request URL.
            - Sends a GET request to the constructed URL.
            - If the response status code is 200, decodes the rates from the response and returns them.
            - Otherwise, raises a RatesNotAvailableError."""
        
        date_str = self._get_date_string(date_obj)
        payload = {'base': base_cur, 'rtype': 'fpy'}
        source_url = self._source_url() + date_str
        response = safe_requests.get(source_url, params=payload, timeout=60)
        if response.status_code == 200:
            rates = self._decode_rates(response, date_str=date_str)
            return rates
        raise RatesNotAvailableError("Currency Rates Source Not Ready")

    def get_rate(self, base_cur, dest_cur, date_obj=None):
        """Function:
        def get_rate(self, base_cur, dest_cur, date_obj=None):
            Retrieves the currency exchange rate between the base currency and the destination currency for a given date.
            Parameters:
                - base_cur (str): The base currency code.
                - dest_cur (str): The destination currency code.
                - date_obj (datetime, optional): The date for which the exchange rate is requested. Defaults to None, which uses the current date.
            Returns:
                - float: The exchange rate between the base currency and the destination currency.
            Processing Logic:
                - Retrieves the date string for the given date object.
                - Constructs the payload and source URL for the API request.
                - Sends a GET request to the API and retrieves the response.
                - Parses the response and returns the exchange rate.
                - If the response status code is not 200, raises a RatesNotAvailableError.
            Example:
                get_rate('USD', 'EUR', datetime(2021, 1, 1))
                # Returns the exchange rate between USD and EUR on January 1, 2021.
            # Function code goes here"""
        
        if base_cur == dest_cur:
            if self._force_decimal:
                return Decimal(1)
            return 1.
        date_str = self._get_date_string(date_obj)
        payload = {'base': base_cur, 'symbols': dest_cur, 'rtype': 'fpy'}
        source_url = self._source_url() + date_str
        response = safe_requests.get(source_url, params=payload, timeout=60)
        if response.status_code == 200:
            rate = self._get_decoded_rate(response, dest_cur, date_str=date_str)
            if not rate:
                raise RatesNotAvailableError("Currency Rate {0} => {1} not available for Date {2}".format(
                    base_cur, dest_cur, date_str))
            return rate
        raise RatesNotAvailableError("Currency Rates Source Not Ready")

    def convert(self, base_cur, dest_cur, amount, date_obj=None):
        """Converts an amount from one currency to another using the latest exchange rate from a specified date.
        Parameters:
            - base_cur (str): The base currency to convert from.
            - dest_cur (str): The destination currency to convert to.
            - amount (Decimal or float): The amount to be converted.
            - date_obj (datetime object, optional): The date for which the exchange rate should be used. If not provided, the latest available rate will be used.
        Returns:
            - converted_amount (Decimal or float): The converted amount in the destination currency.
        Processing Logic:
            - Checks if the amount is a Decimal or float.
            - If base_cur and dest_cur are the same, returns the same amount.
            - Gets the date string from the date_obj.
            - Constructs the payload and source URL.
            - Sends a request to the source URL.
            - If the response is successful, gets the decoded rate for the destination currency.
            - If the rate is not available, raises a RatesNotAvailableError.
            - If the rate is available, multiplies it with the amount to get the converted amount.
            - If the amount is not a Decimal and force_decimal is True, raises a DecimalFloatMismatchError.
            - If the response is not successful, raises a RatesNotAvailableError."""
        
        if isinstance(amount, Decimal):
            use_decimal = True
        else:
            use_decimal = self._force_decimal

        if base_cur == dest_cur:  # Return same amount if both base_cur, dest_cur are same
            if use_decimal:
                return Decimal(amount)
            return float(amount)

        date_str = self._get_date_string(date_obj)
        payload = {'base': base_cur, 'symbols': dest_cur, 'rtype': 'fpy'}
        source_url = self._source_url() + date_str
        response = safe_requests.get(source_url, params=payload, timeout=60)
        if response.status_code == 200:
            rate = self._get_decoded_rate(
                response, dest_cur, use_decimal=use_decimal, date_str=date_str)
            if not rate:
                raise RatesNotAvailableError("Currency {0} => {1} rate not available for Date {2}.".format(
                    source_url, dest_cur, date_str))
            try:
                converted_amount = rate * amount
                return converted_amount
            except TypeError:
                raise DecimalFloatMismatchError(
                    "convert requires amount parameter is of type Decimal when force_decimal=True")
        raise RatesNotAvailableError("Currency Rates Source Not Ready")


_CURRENCY_FORMATTER = CurrencyRates()

get_rates = _CURRENCY_FORMATTER.get_rates
get_rate = _CURRENCY_FORMATTER.get_rate
convert = _CURRENCY_FORMATTER.convert


class CurrencyCodes:

    def __init__(self):
        """"This function initializes the currency data to None."
        Parameters:
            - None
        Returns:
            - None
        Processing Logic:
            - Initialize currency data to None."""
        
        self.__currency_data = None

    @property
    def _currency_data(self):
        """"""
        
        if self.__currency_data is None:
            file_path = os.path.dirname(os.path.abspath(__file__))
            with open(file_path + '/raw_data/currencies.json') as f:
                self.__currency_data = json.loads(f.read())
        return self.__currency_data

    def _get_data(self, currency_code):
        """"""
        
        currency_dict = next((item for item in self._currency_data if item["cc"] == currency_code), None)
        return currency_dict

    def _get_data_from_symbol(self, symbol):
        """"""
        
        currency_dict = next((item for item in self._currency_data if item["symbol"] == symbol), None)
        return currency_dict

    def get_symbol(self, currency_code):
        """"""
        
        currency_dict = self._get_data(currency_code)
        if currency_dict:
            return currency_dict.get('symbol')
        return None

    def get_currency_name(self, currency_code):
        """"""
        
        currency_dict = self._get_data(currency_code)
        if currency_dict:
            return currency_dict.get('name')
        return None

    def get_currency_code_from_symbol(self, symbol):
        """"""
        
        currency_dict = self._get_data_from_symbol(symbol)
        if currency_dict:
            return currency_dict.get('cc')
        return None


_CURRENCY_CODES = CurrencyCodes()

get_symbol = _CURRENCY_CODES.get_symbol
get_currency_name = _CURRENCY_CODES.get_currency_name
get_currency_code_from_symbol = _CURRENCY_CODES.get_currency_code_from_symbol
