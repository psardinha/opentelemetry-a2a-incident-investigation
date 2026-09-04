package pt.example.stringutils.controller;

import jakarta.validation.constraints.NotBlank;
import pt.example.stringutils.service.StringUtilsService;

import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/strings")
@Validated
public class StringUtilsController {
  private final StringUtilsService stringUtilsService;

  public StringUtilsController(StringUtilsService stringUtilsService) {
    this.stringUtilsService = stringUtilsService;
  }

  @GetMapping(value = "/length", produces = MediaType.APPLICATION_JSON_VALUE)
  public Map<String, Object> length(@RequestParam @NotBlank String value) {
    return Map.of("value", value, "length", stringUtilsService.length(value));
  }

  @GetMapping(value = "/reverse", produces = MediaType.APPLICATION_JSON_VALUE)
  public Map<String, Object> reverse(@RequestParam @NotBlank String value) {
    return Map.of("value", value, "reversed", stringUtilsService.reverse(value));
  }
  
  @GetMapping(value = "/upper", produces = MediaType.APPLICATION_JSON_VALUE)
  public Map<String, Object> upper(@RequestParam @NotBlank String value) {
    return Map.of("value", value, "uppper", stringUtilsService.toUpper(value));
  }  
}
