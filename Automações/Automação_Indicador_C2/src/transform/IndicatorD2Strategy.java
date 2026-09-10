package transform;

import model.Indicators;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class IndicatorD2Strategy implements IndicatorStrategy{

    private static final Pattern REGEX_D2 = Pattern.compile("D2:\\s* Não registrou 2 visitas até\\s*(\\d{2}/\\d{2}/\\d{4})");
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    @Override
    public void process(String patientBlock, Indicators indicator) {

        Matcher matcher = REGEX_D2.matcher(patientBlock);


        if(matcher.find()){
            String dateVisit = matcher.group(1);

            try {

                LocalDate dateParsed = LocalDate.parse(dateVisit, DATE_FORMATTER);
                indicator.setDateIndicatorsD2(dateParsed);

            } catch(DateTimeParseException e){
                System.err.println("A data capturada no indicador D2 está inválida, motivo:" + e.getMessage());
            }

        }

    }
}
