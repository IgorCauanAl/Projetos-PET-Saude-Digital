package transform;

import model.Indicators;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class IndicatorD1Strategy implements  IndicatorStrategy{

    private static final Pattern REGEX_D1 = Pattern.compile("D1:\\s* Não registrou 1 visita até\\s*(\\d{2}/\\d{2}/\\d{4})");
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("dd/MM/yyyy");


    @Override
    public void process(String patientBlock, Indicators indicator) {

        Matcher matcher = REGEX_D1.matcher(patientBlock);

        if(matcher.find()){
            String dateVisit = matcher.group(1);

            try {

                LocalDate dateParsed = LocalDate.parse(dateVisit, DATE_FORMATTER);
                indicator.setDateIndicatorsD1(dateParsed);

            } catch(DateTimeParseException e){
                System.err.println("A data capturada no indicador D1 está inválida, motivo:" + e.getMessage());
            }

        }

    }
}
