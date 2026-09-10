package transform;

import model.Indicators;
import model.Patient;

public interface IndicatorStrategy {

    void process(String patientBlock, Indicators indicator);


}
