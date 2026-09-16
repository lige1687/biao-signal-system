import unittest
from metrics import summarize

def result(points):
    return {'daily':[dict(date=d,nav=n,equity=n*100,total_funding=100,
                         assets=n*100,cash=0,receivable=0,fees=0) for d,n in points]}

class ParentReview(unittest.TestCase):
    def test_equal_peak_moves_recovery_anchor(self):
        r=summarize(result([('2020-01-01',1),('2020-01-10',1),('2020-01-11',.9)]))
        self.assertEqual(r['longest_drawdown_days'],1)
    def test_recovered_equal_peak_precedes_new_decline(self):
        r=summarize(result([('2020-01-01',1),('2020-01-02',.9),('2020-01-03',1),('2020-01-04',.8)]))
        self.assertEqual(r['longest_drawdown_days'],2)
    def test_historical_loss_and_peak_anchor(self):
        r=summarize(result([('2020-01-01',1),('2020-01-02',.5),('2020-01-04',1.2)]))
        self.assertEqual(r['longest_drawdown_days'],3)
        self.assertEqual(r['worst_below_funding'],-50)

if __name__=='__main__':unittest.main()
