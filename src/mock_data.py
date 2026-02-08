# Mock data for Audi TT RS (based on reference)
MOCK_CAR_DATA = {
    'make': 'Audi',
    'model': 'TT RS',
    'year': '2016-2023',
    'specs': {
        'Engine': '2.5L TFSI',
        'Power': '394 HP',
        'Torque': '480 Nm',
        'Weight': '1450 kg',
        '0-100 km/h': '3.7 s',
        'Top speed': '250 km/h'
    },
    'country_code': 'de',
    # Using a placeholder image or we will generate one
    'image_path': 'assets/audi_tt_rs_mock.jpg' 
}

# Mapping: Car Make -> Country Code
MAKE_COUNTRIES = {
    # Germany
    'audi': 'de', 'bmw': 'de', 'mercedes': 'de', 'mercedes-benz': 'de',
    'volkswagen': 'de', 'vw': 'de', 'porsche': 'de', 'opel': 'de',
    # Japan
    'toyota': 'jp', 'honda': 'jp', 'nissan': 'jp', 'mazda': 'jp', 
    'subaru': 'jp', 'mitsubishi': 'jp', 'lexus': 'jp', 'infiniti': 'jp',
    'suzuki': 'jp', 'acura': 'jp',
    # USA
    'ford': 'us', 'chevrolet': 'us', 'chevy': 'us', 'tesla': 'us', 
    'dodge': 'us', 'jeep': 'us', 'cadillac': 'us', 'buick': 'us',
    'chrysler': 'us', 'gmc': 'us', 'lincoln': 'us',
    # Italy
    'ferrari': 'it', 'lamborghini': 'it', 'fiat': 'it', 'alfa romeo': 'it',
    'maserati': 'it', 'pagani': 'it',
    # France
    'peugeot': 'fr', 'renault': 'fr', 'citroen': 'fr', 'bugatti': 'fr',
    # UK
    'jaguar': 'gb', 'land rover': 'gb', 'bentley': 'gb', 'rolls-royce': 'gb',
    'aston martin': 'gb', 'mclaren': 'gb', 'lotus': 'gb', 'mini': 'gb',
    # South Korea
    'hyundai': 'kr', 'kia': 'kr', 'genesis': 'kr',
}

def get_country_for_make(make_name):
    """Returns country code for a car make."""
    return MAKE_COUNTRIES.get(make_name.lower(), 'de')  # Default to Germany
