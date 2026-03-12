package lingutechies.vnlawadvisor.lawservice.VBPL;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.data.domain.Page;
import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/v1/vbpl")
@RequiredArgsConstructor
public class VBPLController {
    private final VBPLService VBPLService;

    @GetMapping("")
    public Page<VBPL> getAllVBPL(
            @RequestParam Optional<Integer> pageNo,
            @RequestParam Optional<Integer> pageSize,
            @RequestParam Optional<String> loai,
            @RequestParam Optional<String> name){
        return VBPLService.getAllVBPL(pageNo, pageSize, loai, name);
    }

    @GetMapping("/{vbplId}")
    public VBPL getVBPLbyID(@PathVariable Integer vbplId){
        return VBPLService.getVBPLbyID(vbplId);
    }
}
