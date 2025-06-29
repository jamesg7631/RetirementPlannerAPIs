from tax_band import TaxBand
class TaxBands:

    def __init__(self, tax_bands=None, residency=None, armed_forces=None):
        if tax_band == None and residency == None:
            raise Exception("Tax bands or region must be specified")
        if ((tax_bands is None and residency == "England") or (tax_bands == None and armed_forces == True) or
                (tax_bands is None and residency == "Northern_Ireland")) or (tax_bands is None and residency == "Wales"):
            tax_bands = [TaxBand(12570, 20), TaxBand(50270, 40),
                         TaxBand(125140, 45)]
        elif tax_bands is None and residency == "Scotland":
            tax_bands = [TaxBand(12570, 19), TaxBand(15397, 20)
                , TaxBand(27491, 21), TaxBand(43662, 42),
                         TaxBand(75000, 45), TaxBand(125140, 48)]

        self.tax_bands = tax_bands
        self.loss_taxable_allowance_threshold = 100000

    def yearly_tax_contribution(self, yearly_gross_salary):
        current_amount = yearly_gross_salary
        tax_contribution = 0.0
        yearly_bands = self.band_adjustment(yearly_gross_salary)

        yearly_bands = reversed(yearly_bands)

        for tax_band in yearly_bands:
            if current_amount > tax_band.band:
                tax_contribution += (current_amount - tax_band.band) * (tax_band.tax_percentage / 100)
                current_amount = tax_band.band

        return tax_contribution

    def band_adjustment(self, yearly_gross_salary):
        new_bands = []
        band_reduction = 0
        first_band = self.tax_bands[0]
        excess = yearly_gross_salary - self.loss_taxable_allowance_threshold
        if excess > 0:
            band_reduction = min(excess, first_band.band * 2) / 2

        for tax_band in self.tax_bands:
            if tax_band.band < self.loss_taxable_allowance_threshold:
                new_tax_band = TaxBand(tax_band.band - band_reduction, tax_band.tax_percentage)
            else:
                new_tax_band = TaxBand(tax_band.band, tax_band.tax_percentage)
            new_bands.append(new_tax_band)

        return new_bands


if __name__ == "__main__":
    tax_band = TaxBands()
    print(tax_band.yearly_tax_contribution(100010)/ 52)




