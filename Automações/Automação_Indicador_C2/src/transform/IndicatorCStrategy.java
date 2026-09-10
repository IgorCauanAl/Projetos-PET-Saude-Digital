package transform;

import model.Indicators;

import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class IndicatorCStrategy implements  IndicatorStrategy{

    private static final Pattern REGEX_C = Pattern.compile("C:\\s*Registrar mais (\\d+) aferição\\(ões\\).*? até\\s*(\\d{2}/\\d{2}/\\d{4}) ");
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    @Override
    public void process(String patientBlock, Indicators indicator) {

        Matcher matcher =  REGEX_C.matcher(patientBlock);
        if(matcher.find()){
            String textMeasurement = matcher.group(1);
            String dateMeasurement = matcher.group(2);

            try{
                Integer integerConversion = Integer.parseInt(textMeasurement);
                indicator.setMeasurementC(integerConversion);

                LocalDate dateParsed = LocalDate.parse(dateMeasurement, DATE_FORMATTER);
                indicator.setDateIndicatorsC(dateParsed);

            } catch (NumberFormatException | DateTimeException e){

                System.err.println("Aviso: Falha ao converter dados do Indicador C. Motivo: " + e.getMessage());


            }
        }

    }
}
